#include "worker/executor.hpp"
#include "util/file.hpp"
#include "util/flags.hpp"
#include "util/union_promise.hpp"
#include "util/which.hpp"
#include "whereami++.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <thread>

#include <kj/async-io.h>
#include <kj/debug.h>
#include <kj/io.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <csignal>

#include <spawn.h>

// needed on osx
extern char** environ;  // NOLINT

namespace {

kj::Promise<sandbox::ExecutionInfo> RunSandbox(
    const sandbox::ExecutionOptions& exec_options,
    kj::LowLevelAsyncIoProvider* async_io_provider, uint32_t frontend_id,
    const std::set<uint32_t>& canceled_frontends,
    std::unordered_map<uint32_t, std::set<int>>* running) {
  KJ_LOG(INFO, "Starting sandbox");
  int options_pipe[2];
  int ret = pipe(options_pipe);
  KJ_ASSERT(ret != -1, "pipe", strerror(errno));
  int outcome_pipe[2];
  ret = pipe(outcome_pipe);
  KJ_ASSERT(ret != -1, "pipe", strerror(errno));

  posix_spawn_file_actions_t actions;
  posix_spawn_file_actions_init(&actions);
  posix_spawn_file_actions_addclose(&actions, options_pipe[1]);
  posix_spawn_file_actions_addclose(&actions, outcome_pipe[0]);
  posix_spawn_file_actions_adddup2(&actions, options_pipe[0], fileno(stdin));
  posix_spawn_file_actions_adddup2(&actions, outcome_pipe[1], fileno(stdout));
  posix_spawn_file_actions_addclose(&actions, options_pipe[0]);
  posix_spawn_file_actions_addclose(&actions, outcome_pipe[1]);

  std::string self = whereami::getExecutablePath();
#define VPARAM(s) (s), (s) + strlen(s) + 1
  std::vector<char> self_mut(VPARAM(self.c_str()));
  std::vector<char> sandbox_mut(VPARAM("sandbox"));
  std::vector<char> bin_mut(VPARAM("--bin"));
#undef VPARAM
  char* args[] = {self_mut.data(), sandbox_mut.data(), bin_mut.data(), nullptr};
  int pid;
  KJ_ASSERT(posix_spawn(&pid, args[0], &actions, nullptr, args, environ) == 0,
            strerror(errno));
  close(options_pipe[0]);
  close(outcome_pipe[1]);
  KJ_ASSERT(pid != -1, strerror(errno));

  (*running)[frontend_id].insert(pid);

  kj::Own<kj::AsyncOutputStream> out =
      async_io_provider->wrapOutputFd(options_pipe[1]);
  kj::Own<kj::AsyncInputStream> in =
      async_io_provider->wrapInputFd(outcome_pipe[0]);
  kj::Own<sandbox::ExecutionOptions> ex_opts =
      kj::heap<sandbox::ExecutionOptions>(exec_options);
  return out->write(ex_opts.get(), sizeof(exec_options))
      .attach(std::move(out), std::move(ex_opts))
      .then([fd = options_pipe[1], outcome_pipe, pid, in = std::move(in),
             running, frontend_id, &canceled_frontends]() mutable {
        close(fd);
        auto promise = in->readAllBytes();
        return promise.attach(std::move(in))
            .then([pid, fd = outcome_pipe[0], running, &canceled_frontends,
                   frontend_id](const kj::Array<kj::byte>& data) {
              close(fd);
              if (canceled_frontends.count(frontend_id)) {
                sandbox::ExecutionInfo info;
                info.killed_external = true;
                return info;
              }
              int ret = 0;
              int err = waitpid(pid, &ret, 0);
              (*running)[frontend_id].erase(pid);
              KJ_ASSERT(err != -1, strerror(errno));
              KJ_ASSERT(ret == 0, "Sandbox failed");
              KJ_ASSERT(data.size() >= sizeof(size_t));
              size_t error_sz =
                  *reinterpret_cast<const size_t*>(data.begin());  // NOLINT
              KJ_ASSERT(data.size() >= sizeof(size_t) + error_sz);
              const char* msg =
                  reinterpret_cast<const char*>(data.begin()) +  // NOLINT
                  sizeof(size_t);
              KJ_ASSERT(!error_sz,
                        std::string(msg, data.size() - sizeof(size_t)));
              sandbox::ExecutionInfo outcome;
              memcpy(&outcome, msg, sizeof(outcome));
              return outcome;
            });
      });
}

void PrepareFile(const std::string& path, const util::SHA256_t& hash,
                 bool executable, worker::Cache* cache_) {
  if (hash.isZero()) return;
  cache_->Register(hash);
  util::File::Copy(util::File::PathForHash(hash), path);
  if (executable) {
    util::File::MakeExecutable(path);
  } else {
    util::File::MakeImmutable(path);
  }
}

void RetrieveFile(const std::string& path, capnproto::SHA256::Builder hash_out,
                  worker::Cache* cache_) {
  auto hash = util::File::Hash(path);
  hash.ToCapnp(hash_out);
  util::File::Copy(path, util::File::PathForHash(hash));
  util::File::MakeImmutable(util::File::PathForHash(hash));
  cache_->Register(hash);
}

bool ValidateFileName(std::string name, capnproto::Result::Builder result_) {
  auto set_invalid_request = [&result_](std::string err) {
    for (auto result : result_.getProcesses()) {
      result.getStatus().setInvalidRequest(err);
    }
  };
  if (('/' + name + '/').find("/../") != std::string::npos) {
    set_invalid_request("File names should not contain a .. component!");
    return false;
  }
  if (name.find('\0') != std::string::npos) {
    set_invalid_request("File names should not contain NUL!");
    return false;
  }
  if (name[0] == '/') {
    set_invalid_request("File names should not start with /!");
    return false;
  }
  return true;
}

}  // namespace

namespace worker {

kj::Promise<void> Executor::Execute(capnproto::Request::Reader request_,
                                    capnproto::Result::Builder result_) {
  bool scheduled = false;
  KJ_DEFER(if (!scheduled) manager_->CancelPending());
  for (auto request : request_.getProcesses()) {
    auto executable = request.getExecutable();
    for (const auto& input : request.getInputFiles()) {
      if (!ValidateFileName(input.getName(), result_)) return kj::READY_NOW;
    }
    for (const auto& fifo : request.getFifos()) {
      if (!ValidateFileName(fifo.getName(), result_)) return kj::READY_NOW;
    }
    for (const auto& output : request.getOutputFiles()) {
      if (!ValidateFileName(output, result_)) return kj::READY_NOW;
    }
    if (executable.isLocalFile()) {
      if (!ValidateFileName(executable.getLocalFile().getName(), result_)) {
        return kj::READY_NOW;
      }
    }
  }

  auto fail = [result_](const std::string& error) mutable {
    for (auto result : result_.getProcesses()) {
      result.getStatus().setInternalError(error);
    }
    return kj::READY_NOW;
  };

  util::TempDir fifo_tmp_(Flags::temp_directory);

  auto add_fifo = [&fifo_tmp_, fail](const std::string dest,
                                     uint32_t id) mutable {
    std::string src =
        util::File::JoinPath(fifo_tmp_.Path(), std::to_string(id));
    if (access(src.c_str(), F_OK) == -1) {
      if (errno != ENOENT) {
        fail("access: " + std::string(strerror(errno)));
        return false;
      }
      if (mkfifo(src.c_str(), S_IRWXU) == -1) {
        fail("mkfifo: " + std::string(strerror(errno)));
        return false;
      }
    }
    if (link(src.c_str(), dest.c_str()) == -1) {
      fail("link: " + std::string(strerror(errno)));
      return false;
    }
    return true;
  };

  size_t num_processes = request_.getProcesses().size();
  util::UnionPromiseBuilder builder;
  std::vector<util::TempDir> tmp;
  while (tmp.size() < num_processes) tmp.emplace_back(Flags::temp_directory);
  std::vector<std::string> cmdlines(num_processes);
  std::vector<std::string> exes(num_processes);
  std::vector<std::string> sandbox_dirs(num_processes);
  std::vector<std::string> stderr_paths(num_processes);
  std::vector<std::string> stdout_paths(num_processes);
  std::vector<sandbox::ExecutionOptions> exec_options_v;
  result_.initProcesses(num_processes);
  for (size_t i = 0; i < request_.getProcesses().size(); i++) {
    auto request = request_.getProcesses()[i];
    auto executable = request.getExecutable();
    auto& cmdline = cmdlines[i];
    auto& exe = exes[i];
    auto& sandbox_dir = sandbox_dirs[i];
    auto& stdout_path = stdout_paths[i];
    auto& stderr_path = stderr_paths[i];
    switch (executable.which()) {
      case capnproto::ProcessRequest::Executable::SYSTEM:
        cmdline = executable.getSystem();
        if (cmdline.empty()) return fail("Empty command name");
        if (cmdline[0] != '/') {
          if (cmdline.find('/') != std::string::npos) {
            return fail("Relative path cannot have /");
          }
          cmdline = util::which(cmdline);
          if (cmdline.empty()) {
            for (auto result : result_.getProcesses()) {
              result.getStatus().setInvalidRequest(
                  "Cannot find system program: " +
                  std::string(executable.getSystem()));
            }
            return kj::READY_NOW;
          }
        }
        break;
      case capnproto::ProcessRequest::Executable::LOCAL_FILE:
        cmdline = executable.getLocalFile().getName();
        break;
    }

    for (const auto& input : request.getInputFiles()) {
      builder.AddPromise(util::File::MaybeGet(input.getHash(), server_));
    }
    if (request.getStdin().isHash()) {
      builder.AddPromise(
          util::File::MaybeGet(request.getStdin().getHash(), server_));
    }
    if (executable.isLocalFile()) {
      builder.AddPromise(
          util::File::MaybeGet(executable.getLocalFile().getHash(), server_));
    }

    exe = cmdline;
    if (request.getArgs().size() != 0) {
      for (const std::string& arg : request.getArgs())  // NOLINT
        cmdline += " '" + arg + "'";
    }

    if (Flags::keep_sandboxes) {
      tmp[i].Keep();
      std::ofstream cmdline_file(
          util::File::JoinPath(tmp[i].Path(), "command.txt"));
      cmdline_file << cmdline << std::endl;
    }

    auto log = kj::str("Executing:\n", "\tCommand:        ", cmdline, "\n",
                       "\tInside sandbox: ", tmp[i].Path());
    KJ_LOG(INFO, log);

    sandbox_dir = util::File::JoinPath(tmp[i].Path(), kBoxDir);
    util::File::MakeDirs(sandbox_dir);

    exec_options_v.emplace_back(sandbox_dir, exe);

    auto& exec_options = exec_options_v.back();

    // Folder and arguments.
    exec_options.SetArgs(request.getArgs());

    if (executable.isLocalFile()) {
      exec_options.prepare_executable = true;
    }

    // Stdout/err files.
    stdout_path = util::File::JoinPath(tmp[i].Path(), "stdout");
    stderr_path = util::File::JoinPath(tmp[i].Path(), "stderr");
    sandbox::ExecutionOptions::stringcpy(exec_options.stdout_file, stdout_path);
    sandbox::ExecutionOptions::stringcpy(exec_options.stderr_file, stderr_path);

    // FIFOs.
    for (auto fifo : request.getFifos()) {
      if (!add_fifo(util::File::JoinPath(sandbox_dir, fifo.getName()),
                    fifo.getId())) {
        return kj::READY_NOW;
      }
    }
    if (request.getStdin().isFifo() && request.getStdin().getFifo() != 0) {
      auto stdin_path = util::File::JoinPath(tmp[i].Path(), "stdin");
      if (!add_fifo(stdin_path, request.getStdin().getFifo())) {
        return kj::READY_NOW;
      }
      sandbox::ExecutionOptions::stringcpy(exec_options_v[i].stdin_file,
                                           stdin_path);
    }
    if (request.getStdout() != 0) {
      if (!add_fifo(stdout_path, request.getStdout())) {
        return kj::READY_NOW;
      }
      sandbox::ExecutionOptions::stringcpy(exec_options_v[i].stdout_file,
                                           stdout_path);
    }
    if (request.getStderr() != 0) {
      if (!add_fifo(stderr_path, request.getStderr())) {
        return kj::READY_NOW;
      }
      sandbox::ExecutionOptions::stringcpy(exec_options_v[i].stderr_file,
                                           stderr_path);
    }

    // Limits.
    // Scale up time limits to have a good margin for random occurrences.
    auto limits = request.getLimits();
    exec_options.cpu_limit_millis = limits.getCpuTime() * 1200 +  // NOLINT
                                    request.getExtraTime() * 1000;
    exec_options.wall_limit_millis = limits.getWallTime() * 1200 +  // NOLINT
                                     request.getExtraTime() * 1000;
    exec_options.memory_limit_kb = limits.getMemory() * 1.2;  // NOLINT
    exec_options.max_files = limits.getNofiles();
    exec_options.max_procs = limits.getNproc();
    exec_options.max_file_size_kb = limits.getFsize();
    exec_options.max_mlock_kb = limits.getMemlock();
    exec_options.max_stack_kb = limits.getStack();
  }

  scheduled = true;
  return std::move(builder).Finalize().then(
      [sandbox_dirs, exec_options_v, request_, result_, stderr_paths,
       stdout_paths, fail, tmp = std::move(tmp), num_processes,
       this]() mutable -> kj::Promise<void> {
        KJ_LOG(INFO, "Files loaded, starting sandbox setup");
        for (size_t i = 0; i < request_.getProcesses().size(); i++) {
          auto request = request_.getProcesses()[i];
          auto executable = request.getExecutable();
          if (executable.isLocalFile()) {
            auto local_file = executable.getLocalFile();
            PrepareFile(
                util::File::JoinPath(sandbox_dirs[i], local_file.getName()),
                local_file.getHash(), true, cache_);
          }
          if (request.getStdin().isHash() &&
              !util::SHA256_t(request.getStdin().getHash()).isZero()) {
            auto stdin_path = util::File::JoinPath(tmp[i].Path(), "stdin");
            PrepareFile(stdin_path, request.getStdin().getHash(), false,
                        cache_);
            sandbox::ExecutionOptions::stringcpy(exec_options_v[i].stdin_file,
                                                 stdin_path);
          }
          for (const auto& input : request.getInputFiles()) {
            PrepareFile(util::File::JoinPath(sandbox_dirs[i], input.getName()),
                        input.getHash(), input.getExecutable(), cache_);
          }
        }

        // Actual execution.
        return manager_
            ->ScheduleTask(
                request_.getExclusive() ? manager_->NumCores() : num_processes,
                std::function<kj::Promise<kj::Array<sandbox::ExecutionInfo>>()>(
                    [this, frontend_id = request_.getEvaluationId(),
                     exec_options_v, num_processes]() {
                      kj::Vector<kj::Promise<sandbox::ExecutionInfo>> info_(
                          num_processes);
                      for (size_t i = 0; i < num_processes; i++) {
                        info_.add(RunSandbox(
                            exec_options_v[i],
                            &manager_->Client().getLowLevelIoProvider(),
                            frontend_id, canceled_evaluations_, &running_));
                      }
                      return kj::joinPromises(info_.releaseAsArray());
                    }))
            .then(
                [result_, exec_options_v, stdout_paths, stderr_paths, request_,
                 sandbox_dirs, tmp = std::move(tmp), num_processes, fail,
                 this](kj::Array<sandbox::ExecutionInfo> outcomes) mutable {
                  KJ_LOG(INFO, "Sandbox done, processing results");
                  for (size_t i = 0; i < num_processes; i++) {
                    auto result = result_.getProcesses()[i];
                    auto request = request_.getProcesses()[i];
                    auto& outcome = outcomes[i];
                    auto& stdout_path = stdout_paths[i];
                    auto& stderr_path = stderr_paths[i];
                    auto& sandbox_dir = sandbox_dirs[i];
                    if (outcome.killed_external) {
                      fail("Killed externally");
                      return;
                    }
                    result.setWasKilled(outcome.killed);
                    // Resource usage.
                    auto resource_usage = result.initResourceUsage();
                    resource_usage.setCpuTime(outcome.cpu_time_millis / 1000.0);
                    resource_usage.setSysTime(outcome.sys_time_millis / 1000.0);
                    resource_usage.setWallTime(outcome.wall_time_millis /
                                               1000.0);
                    resource_usage.setMemory(outcome.memory_usage_kb);

                    auto limits = request.getLimits();
                    if (limits.getMemory() != 0 &&
                        static_cast<uint64_t>(outcome.memory_usage_kb) >=
                            limits.getMemory()) {
                      result.getStatus().setMemoryLimit();
                    } else if (limits.getCpuTime() != 0 &&
                               outcome.cpu_time_millis +
                                       outcome.sys_time_millis >=
                                   limits.getCpuTime() * 1000) {
                      result.getStatus().setTimeLimit();
                    } else if (limits.getWallTime() != 0 &&
                               outcome.wall_time_millis >=
                                   limits.getWallTime() * 1000) {
                      result.getStatus().setWallLimit();
                    } else if (outcome.signal != 0) {
                      result.getStatus().setSignal(outcome.signal);
                    } else if (outcome.status_code != 0) {
                      result.getStatus().setReturnCode(outcome.status_code);
                    } else {
                      result.getStatus().setSuccess();
                    }

                    // Output files.
                    if (request.getStdout() == 0) {
                      RetrieveFile(stdout_path, result.initStdout(), cache_);
                    }
                    if (request.getStderr() == 0) {
                      RetrieveFile(stderr_path, result.initStderr(), cache_);
                    }
                    auto output_names = request.getOutputFiles();
                    auto outputs = result.initOutputFiles(output_names.size());
                    for (size_t i = 0; i < request.getOutputFiles().size();
                         i++) {
                      outputs[i].setName(output_names[i]);
                      try {
                        RetrieveFile(
                            util::File::JoinPath(sandbox_dir, output_names[i]),
                            outputs[i].initHash(), cache_);
                      } catch (const std::system_error& exc) {
                        if (exc.code().value() !=
                            static_cast<int>(
                                std::errc::no_such_file_or_directory)) {
                          result.getStatus().setInternalError(exc.what());
                        } else {
                          if (result.getStatus().isSuccess()) {
                            result.getStatus().setMissingFiles();
                          }
                        }
                      }
                    }
                  }
                },
                [fail](kj::Exception exc) mutable {
                  KJ_LOG(WARNING, "Execution failed: ", exc.getDescription());
                  fail(exc.getDescription());
                })
            .eagerlyEvaluate(nullptr);
      },
      [this](kj::Exception exc) -> kj::Promise<void> {
        KJ_LOG(WARNING, "Execution canceled: ", exc.getDescription());
        manager_->CancelPending();
        return exc;
      });
}

kj::Promise<void> Executor::cancelRequest(CancelRequestContext context) {
  uint32_t evaluation_id = context.getParams().getEvaluationId();
  KJ_LOG(INFO,
         "Cancelling evaluations of frontend " + std::to_string(evaluation_id));
  canceled_evaluations_.insert(evaluation_id);
  for (int pid : running_[evaluation_id]) {
    kill(pid, SIGINT);
  }
  return kj::READY_NOW;
}

}  // namespace worker
