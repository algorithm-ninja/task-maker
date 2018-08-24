#include "worker/executor.hpp"
#include "util/file.hpp"
#include "util/flags.hpp"
#include "util/misc.hpp"
#include "util/which.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <thread>

#include <kj/async-io.h>
#include <kj/debug.h>
#include <kj/io.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {
kj::Promise<sandbox::ExecutionInfo> RunSandbox(
    sandbox::ExecutionOptions exec_options,
    kj::LowLevelAsyncIoProvider& async_io_provider) {
  int pipefd[2];
  int ret = pipe(pipefd);
  KJ_ASSERT(ret != -1, strerror(errno));
  int pid = fork();
  KJ_ASSERT(pid != -1, strerror(errno));
  if (pid == 0) {  // Child process
    close(pipefd[0]);
    sandbox::ExecutionInfo outcome;
    std::string error_msg;
    std::unique_ptr<sandbox::Sandbox> sb = sandbox::Sandbox::Create();
    kj::FdOutputStream out(pipefd[1]);
    if (!sb->Execute(exec_options, &outcome, &error_msg)) {
      size_t sz = error_msg.size();
      out.write(&sz, sizeof(sz));
      out.write(error_msg.c_str(), sz + 1);
    } else {
      size_t sz = 0;
      out.write(&sz, sizeof(sz));
      out.write(&outcome, sizeof(outcome));
      // TODO: think about outcome.message
    }
    _Exit(0);
  } else {
    close(pipefd[1]);  // Parent process
    kj::Own<kj::AsyncInputStream> in = async_io_provider.wrapInputFd(pipefd[0]);
    auto promise = in->readAllBytes();
    return promise.attach(std::move(in))
        .then([pid](const kj::Array<kj::byte>& data) {
          size_t error_sz = *(size_t*)data.begin();
          const unsigned char* msg = data.begin() + sizeof(size_t);
          KJ_ASSERT(!error_sz, msg);
          sandbox::ExecutionInfo outcome;
          memcpy(&outcome, msg, sizeof(outcome));
          int err = waitpid(pid, nullptr, 0);
          KJ_ASSERT(err != -1, strerror(errno));
          return outcome;
        });
  }
}

void PrepareFile(const std::string& path, const util::SHA256_t& hash,
                 bool executable) {
  if (hash.isZero()) return;
  util::File::Copy(util::File::PathForHash(hash), path);
  if (executable)
    util::File::MakeExecutable(path);
  else
    util::File::MakeImmutable(path);
}

void RetrieveFile(const std::string& path,
                  capnproto::SHA256::Builder hash_out) {
  auto hash = util::File::Hash(path);
  hash.ToCapnp(hash_out);
  util::File::Copy(path, util::File::PathForHash(hash));
  util::File::MakeImmutable(util::File::PathForHash(hash));
}

bool ValidateFileName(std::string name, capnproto::Result::Builder result) {
  // TODO: make this more permissive?
  if (name.find("..") != std::string::npos) {
    result.getStatus().setInternalError("File names should not contain ..!");
    return false;
  }
  if (name.find('\0') != std::string::npos) {
    result.getStatus().setInternalError("File names should not contain NUL!");
    return false;
  }
  if (name[0] == '/') {
    result.getStatus().setInternalError("File names should not start with /!");
    return false;
  }
  return true;
}

}  // namespace

namespace worker {

kj::Promise<void> Executor::Execute(capnproto::Request::Reader request,
                                    capnproto::Result::Builder result) {
  auto executable = request.getExecutable();
  for (const auto& input : request.getInputFiles()) {
    if (!ValidateFileName(input.getName(), result)) return kj::READY_NOW;
  }
  for (const auto& output : request.getOutputFiles()) {
    if (!ValidateFileName(output, result)) return kj::READY_NOW;
  }
  if (executable.isLocalFile()) {
    if (!ValidateFileName(executable.getLocalFile().getName(), result))
      return kj::READY_NOW;
  }

  auto fail = [&result](const std::string& error) {
    result.getStatus().setInternalError(error);
    return kj::READY_NOW;
  };

  std::string cmdline;
  switch (executable.which()) {
    case capnproto::Request::Executable::SYSTEM:
      cmdline = executable.getSystem();
      if (cmdline.empty()) return fail("Empty command name");
      if (cmdline[0] != '/') {
        if (cmdline.find('/') != cmdline.npos)
          return fail("Relative path cannot have /");
        cmdline = util::which(cmdline);
        if (cmdline.empty()) {
          result.getStatus().setMissingExecutable(
              "Cannot find system program: " +
              std::string(executable.getSystem()));
          return kj::READY_NOW;
        }
      }
      break;
    case capnproto::Request::Executable::LOCAL_FILE:
      cmdline = executable.getLocalFile().getName();
      break;
  }

  // TODO: move inside PrepareFile?
  kj::Promise<void> last_load = kj::READY_NOW;
  {
    util::UnionPromiseBuilder builder;
    for (const auto& input : request.getInputFiles()) {
      builder.AddPromise(util::File::MaybeGet(input.getHash(), server_));
    }
    builder.AddPromise(util::File::MaybeGet(request.getStdin(), server_));
    if (executable.isLocalFile()) {
      builder.AddPromise(
          util::File::MaybeGet(executable.getLocalFile().getHash(), server_));
    }
    last_load = std::move(builder).Finalize();
  }

  util::TempDir tmp(Flags::temp_directory);

  std::string exe = cmdline;

  if (request.getArgs().size() != 0)
    for (const std::string& arg : request.getArgs())
      cmdline += " '" + arg + "'";

  if (Flags::keep_sandboxes) {
    tmp.Keep();
    std::ofstream cmdline_file(util::File::JoinPath(tmp.Path(), "command.txt"));
    cmdline_file << cmdline << std::endl;
  }

  auto log = kj::str("Executing:\n", "\tCommand:        ", cmdline, "\n",
                     "\tInside sandbox: ", tmp.Path());
  KJ_LOG(INFO, log);

  std::string sandbox_dir = util::File::JoinPath(tmp.Path(), kBoxDir);
  util::File::MakeDirs(sandbox_dir);

  // Folder and arguments.
  sandbox::ExecutionOptions exec_options(sandbox_dir, exe);
  exec_options.SetArgs(request.getArgs());

  if (executable.isLocalFile()) {
    exec_options.prepare_executable = true;  // TODO: is this useful?
  }

  // Limits.
  // Scale up time limits to have a good margin for random occurrences.
  auto limits = request.getLimits();
  exec_options.cpu_limit_millis =
      limits.getCpuTime() * 1200 + request.getExtraTime();
  exec_options.wall_limit_millis =
      limits.getWallTime() * 1200 + request.getExtraTime();
  exec_options.memory_limit_kb = limits.getMemory() * 1.2;
  exec_options.max_files = limits.getNofiles();
  exec_options.max_procs = limits.getNproc();
  exec_options.max_file_size_kb = limits.getFsize();
  exec_options.max_mlock_kb = limits.getMemlock();
  exec_options.max_stack_kb = limits.getStack();
  // Stdout/err files.
  auto stdout_path = util::File::JoinPath(tmp.Path(), "stdout");
  auto stderr_path = util::File::JoinPath(tmp.Path(), "stderr");
  sandbox::ExecutionOptions::stringcpy(exec_options.stdout_file, stdout_path);
  sandbox::ExecutionOptions::stringcpy(exec_options.stderr_file, stderr_path);

  last_load = last_load.then([executable, sandbox_dir, exec_options, request,
                              result, stderr_path, fail, stdout_path,
                              tmp = std::move(tmp),
                              this]() mutable -> kj::Promise<void> {
    KJ_LOG(INFO, "Files loaded, starting sandbox setup");
    if (executable.isLocalFile()) {
      auto local_file = executable.getLocalFile();
      PrepareFile(util::File::JoinPath(sandbox_dir, local_file.getName()),
                  local_file.getHash(), true);
    }
    if (!util::SHA256_t(request.getStdin()).isZero()) {
      auto stdin_path = util::File::JoinPath(tmp.Path(), "stdin");
      PrepareFile(stdin_path, request.getStdin(), true);
      sandbox::ExecutionOptions::stringcpy(exec_options.stdin_file, stdin_path);
    }
    for (const auto& input : request.getInputFiles()) {
      PrepareFile(util::File::JoinPath(sandbox_dir, input.getName()),
                  input.getHash(), input.getExecutable());
    }

    // Actual execution.
    return manager_
        .ScheduleTask(request.getExclusive() ? manager_.NumCores() : 1,
                      std::function<kj::Promise<sandbox::ExecutionInfo>()>(
                          [this, exec_options]() {
                            return RunSandbox(
                                exec_options,
                                manager_.Client().getLowLevelIoProvider());
                          }))
        .then(
            [result, exec_options, stdout_path, stderr_path, request,
             sandbox_dir,
             tmp = std::move(tmp)](sandbox::ExecutionInfo outcome) mutable {
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
              RetrieveFile(stdout_path, result.initStdout());
              RetrieveFile(stderr_path, result.initStderr());
              auto output_names = request.getOutputFiles();
              auto outputs = result.initOutputFiles(output_names.size());
              for (size_t i = 0; i < request.getOutputFiles().size(); i++) {
                outputs[i].setName(output_names[i]);
                try {
                  RetrieveFile(
                      util::File::JoinPath(sandbox_dir, output_names[i]),
                      outputs[i].initHash());
                } catch (const std::system_error& exc) {
                  if (exc.code().value() !=
                      static_cast<int>(std::errc::no_such_file_or_directory)) {
                    result.getStatus().setInternalError(exc.what());
                  } else {
                    if (result.getStatus().isSuccess()) {
                      result.getStatus().setMissingFiles();
                    }
                  }
                }
              }
            },
            [fail](kj::Exception exc) { fail(exc.getDescription()); })
        .eagerlyEvaluate(nullptr);
  });
  return last_load;
}  // namespace executor

}  // namespace worker
