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

#include <spawn.h>

extern char** environ;

namespace {

kj::Promise<sandbox::ExecutionInfo> RunSandbox(
    const sandbox::ExecutionOptions& exec_options,
    kj::LowLevelAsyncIoProvider& async_io_provider) {
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
#define VPARAM(s) s, s + strlen(s) + 1
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
  kj::Own<kj::AsyncOutputStream> out =
      async_io_provider.wrapOutputFd(options_pipe[1]);
  kj::Own<kj::AsyncInputStream> in =
      async_io_provider.wrapInputFd(outcome_pipe[0]);
  kj::Own<sandbox::ExecutionOptions> ex_opts =
      kj::heap<sandbox::ExecutionOptions>(exec_options);
  return out->write(ex_opts.get(), sizeof(exec_options))
      .attach(std::move(out), std::move(ex_opts))
      .then([fd = options_pipe[1], outcome_pipe, pid,
             in = std::move(in)]() mutable {
        close(fd);
        auto promise = in->readAllBytes();
        return promise.attach(std::move(in))
            .then([pid, fd = outcome_pipe[0]](const kj::Array<kj::byte>& data) {
              close(fd);
              size_t error_sz = *(size_t*)data.begin();
              const unsigned char* msg = data.begin() + sizeof(size_t);
              KJ_ASSERT(!error_sz, msg);
              sandbox::ExecutionInfo outcome;
              memcpy(&outcome, msg, sizeof(outcome));
              int ret = 0;
              int err = waitpid(pid, &ret, 0);
              KJ_ASSERT(err != -1, strerror(errno));
              KJ_ASSERT(ret == 0, "Sandbox failed");
              return outcome;
            });
      });
}

void PrepareFile(const std::string& path, const util::SHA256_t& hash,
                 bool executable, worker::Cache& cache_) {
  if (hash.isZero()) return;
  cache_.Register(hash);
  util::File::Copy(util::File::PathForHash(hash), path);
  if (executable)
    util::File::MakeExecutable(path);
  else
    util::File::MakeImmutable(path);
}

void RetrieveFile(const std::string& path, capnproto::SHA256::Builder hash_out,
                  worker::Cache& cache_) {
  auto hash = util::File::Hash(path);
  hash.ToCapnp(hash_out);
  util::File::Copy(path, util::File::PathForHash(hash));
  util::File::MakeImmutable(util::File::PathForHash(hash));
  cache_.Register(hash);
}

bool ValidateFileName(std::string name, capnproto::Result::Builder result_) {
  // TODO: make this more permissive?
  auto set_internal_error = [&result_](std::string err) {
    for (auto result : result_.getProcesses()) {
      result.getStatus().setInternalError(err);
    }
  };
  if (name.find("..") != std::string::npos) {
    set_internal_error("File names should not contain ..!");
    return false;
  }
  if (name.find('\0') != std::string::npos) {
    set_internal_error("File names should not contain NUL!");
    return false;
  }
  if (name[0] == '/') {
    set_internal_error("File names should not start with /!");
    return false;
  }
  return true;
}

}  // namespace

namespace worker {

kj::Promise<void> Executor::Execute(capnproto::Request::Reader request_,
                                    capnproto::Result::Builder result_) {
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
      if (!ValidateFileName(executable.getLocalFile().getName(), result_))
        return kj::READY_NOW;
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
          if (cmdline.find('/') != cmdline.npos)
            return fail("Relative path cannot have /");
          cmdline = util::which(cmdline);
          if (cmdline.empty()) {
            for (auto result : result_.getProcesses()) {
              result.getStatus().setMissingExecutable(
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
    builder.AddPromise(util::File::MaybeGet(request.getStdin(), server_));
    if (executable.isLocalFile()) {
      builder.AddPromise(
          util::File::MaybeGet(executable.getLocalFile().getHash(), server_));
    }

    exe = cmdline;
    if (request.getArgs().size() != 0)
      for (const std::string& arg : request.getArgs())
        cmdline += " '" + arg + "'";

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
      exec_options.prepare_executable = true;  // TODO: is this useful?
    }

    // FIFOs.
    for (auto fifo : request.getFifos()) {
      if (!add_fifo(util::File::JoinPath(sandbox_dir, fifo.getName()),
                    fifo.getId())) {
        return kj::READY_NOW;
      }
    }

    // Limits.
    // Scale up time limits to have a good margin for random occurrences.
    auto limits = request.getLimits();
    exec_options.cpu_limit_millis =
        limits.getCpuTime() * 1200 + request.getExtraTime() * 1000;
    exec_options.wall_limit_millis =
        limits.getWallTime() * 1200 + request.getExtraTime() * 1000;
    exec_options.memory_limit_kb = limits.getMemory() * 1.2;
    exec_options.max_files = limits.getNofiles();
    exec_options.max_procs = limits.getNproc();
    exec_options.max_file_size_kb = limits.getFsize();
    exec_options.max_mlock_kb = limits.getMemlock();
    exec_options.max_stack_kb = limits.getStack();
    // Stdout/err files.
    stdout_path = util::File::JoinPath(tmp[i].Path(), "stdout");
    stderr_path = util::File::JoinPath(tmp[i].Path(), "stderr");
    sandbox::ExecutionOptions::stringcpy(exec_options.stdout_file, stdout_path);
    sandbox::ExecutionOptions::stringcpy(exec_options.stderr_file, stderr_path);
  }

  return std::move(builder).Finalize().then([sandbox_dirs, exec_options_v,
                                             request_, result_, stderr_paths,
                                             stdout_paths, fail,
                                             tmp = std::move(tmp),
                                             num_processes, this]() mutable
                                            -> kj::Promise<void> {
    KJ_LOG(INFO, "Files loaded, starting sandbox setup");
    for (size_t i = 0; i < request_.getProcesses().size(); i++) {
      auto request = request_.getProcesses()[i];
      auto executable = request.getExecutable();
      if (executable.isLocalFile()) {
        auto local_file = executable.getLocalFile();
        PrepareFile(util::File::JoinPath(sandbox_dirs[i], local_file.getName()),
                    local_file.getHash(), true, cache_);
      }
      if (!util::SHA256_t(request.getStdin()).isZero()) {
        auto stdin_path = util::File::JoinPath(tmp[i].Path(), "stdin");
        PrepareFile(stdin_path, request.getStdin(), false, cache_);
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
        .ScheduleTask(
            request_.getExclusive() ? manager_.NumCores() : num_processes,
            std::function<kj::Promise<kj::Array<sandbox::ExecutionInfo>>()>(
                [this, exec_options_v, num_processes]() {
                  kj::Vector<kj::Promise<sandbox::ExecutionInfo>> info_(
                      num_processes);
                  for (size_t i = 0; i < num_processes; i++) {
                    info_.add(
                        RunSandbox(exec_options_v[i],
                                   manager_.Client().getLowLevelIoProvider()));
                  }
                  return kj::joinPromises(info_.releaseAsArray());
                }))
        .then(
            [result_, exec_options_v, stdout_paths, stderr_paths, request_,
             sandbox_dirs, tmp = std::move(tmp), num_processes,
             this](kj::Array<sandbox::ExecutionInfo> outcomes) mutable {
              KJ_LOG(INFO, "Sandbox done, processing results");
              for (size_t i = 0; i < num_processes; i++) {
                auto result = result_.getProcesses()[i];
                auto request = request_.getProcesses()[i];
                auto& outcome = outcomes[i];
                auto& exec_options = exec_options_v[i];
                auto& stdout_path = stdout_paths[i];
                auto& stderr_path = stderr_paths[i];
                auto& sandbox_dir = sandbox_dirs[i];
                // Resource usage.
                auto resource_usage = result.initResourceUsage();
                resource_usage.setCpuTime(outcome.cpu_time_millis / 1000.0);
                resource_usage.setSysTime(outcome.sys_time_millis / 1000.0);
                resource_usage.setWallTime(outcome.wall_time_millis / 1000.0);
                resource_usage.setMemory(outcome.memory_usage_kb);

                if (exec_options.memory_limit_kb != 0 &&
                    outcome.memory_usage_kb >= exec_options.memory_limit_kb) {
                  result.getStatus().setMemoryLimit();
                } else if (exec_options.cpu_limit_millis != 0 &&
                           outcome.cpu_time_millis + outcome.sys_time_millis >=
                               exec_options.cpu_limit_millis) {
                  result.getStatus().setTimeLimit();
                } else if (exec_options.wall_limit_millis != 0 &&
                           outcome.wall_time_millis >=
                               exec_options.wall_limit_millis) {
                  result.getStatus().setWallLimit();
                } else if (outcome.signal != 0) {
                  result.getStatus().setSignal(outcome.signal);
                } else if (outcome.status_code != 0) {
                  result.getStatus().setReturnCode(outcome.status_code);
                } else {
                  result.getStatus().setSuccess();
                }

                // Output files.
                RetrieveFile(stdout_path, result.initStdout(), cache_);
                RetrieveFile(stderr_path, result.initStderr(), cache_);
                auto output_names = request.getOutputFiles();
                auto outputs = result.initOutputFiles(output_names.size());
                for (size_t i = 0; i < request.getOutputFiles().size(); i++) {
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
            [fail](kj::Exception exc) mutable { fail(exc.getDescription()); })
        .eagerlyEvaluate(nullptr);
  });
}  // namespace executor

}  // namespace worker
