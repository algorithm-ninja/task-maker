#include "sandbox/unix.hpp"

#include <chrono>
#include <thread>

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace sandbox {

bool Unix::Execute(const ExecutionOptions& options, ExecutionInfo* info,
                   std::string* error_msg) {
  options_ = &options;
  if (!Setup(error_msg)) return false;
  if (!DoFork(error_msg)) return false;
  if (!Wait(info, error_msg)) return false;
  return true;
}

bool Unix::Setup(std::string* error_msg) {
  if (pipe(pipe_fds_) == -1) {
    *error_msg = "pipe2: ";
    *error_msg += strerror(errno);
    return false;
  }
  if (fcntl(pipe_fds_[0], F_SETFD, FD_CLOEXEC) == -1 ||
      fcntl(pipe_fds_[1], F_SETFD, FD_CLOEXEC) == -1) {
    *error_msg = "fcntl: ";
    *error_msg += strerror(errno);
    return false;
  }
  return true;
}

bool Unix::DoFork(std::string* error_msg) {
  int fork_result = fork();
  if (fork_result == -1) {
    *error_msg = strerror(errno);
    return false;
  }
  if (fork_result) {
    child_pid_ = fork_result;
    return true;
  } else {
    Child();
  }
}

void Unix::Child() {
  auto die = [this](const char* prefix, const char* err) {
    std::string msg = prefix;
    msg += ": ";
    msg += err;
    int len = msg.size();
    write(pipe_fds_[1], &len, sizeof(len));
    write(pipe_fds_[1], msg.c_str(), len);
    close(pipe_fds_[1]);
    _Exit(1);
  };

  if (chdir(options_->root.c_str()) == -1) {
    die("chdir", strerror(errno));
  }

  // Prepare args.
  std::vector<std::vector<char>> vec_args;
  auto add_arg = [&vec_args](const std::string& arg) {
    vec_args.emplace_back(arg.begin(), arg.end());
    vec_args.back().push_back(0);
  };
  add_arg(options_->executable);
  for (const std::string& arg : options_->args) add_arg(arg);
  std::vector<char*> args;
  for (std::vector<char>& arg : vec_args) args.push_back(arg.data());
  args.push_back(nullptr);

  // Handle I/O redirection.
  close(pipe_fds_[0]);
#define DUP(field, fd)                                    \
  if (options_->field##_fd != -1) {                       \
    int ret = dup2(options_->field##_fd, fd);             \
    if (ret == -1) die("redir " #field, strerror(errno)); \
  }
  DUP(stdin, STDIN_FILENO);
  DUP(stdout, STDOUT_FILENO);
  DUP(stderr, STDERR_FILENO);
#undef DUP

  // Set resource limits.
  struct rlimit rlim;
#define SET_RLIM(res, value)                    \
  {                                             \
    rlim_t lim = value;                         \
    if (lim) {                                  \
      rlim.rlim_cur = value;                    \
      rlim.rlim_max = value;                    \
      if (setrlimit(RLIMIT_##res, &rlim) < 0) { \
        die("setrlim " #res, strerror(errno));  \
      }                                         \
    }                                           \
  }

  SET_RLIM(AS, options_->memory_limit_kb * 1024);
  SET_RLIM(CPU, options_->cpu_limit_millis / 1000);
  SET_RLIM(FSIZE, options_->max_file_size_kb * 1024);
  SET_RLIM(MEMLOCK, options_->max_mlock_kb * 1024);
  SET_RLIM(NOFILE, options_->max_files);
  SET_RLIM(NPROC, options_->max_procs);

  // Setting stack size does not seem to work on MAC.
#ifndef __APPLE__
  SET_RLIM(STACK, options_->max_stack_kb ? options_->max_stack_kb * 1024
                                         : RLIM_INFINITY);
#endif
#undef SET_RLIM

  std::string error_msg;
  if (!OnChild(&error_msg)) {
    die("OnChild", error_msg.c_str());
  }
  execv(options_->executable.c_str(), args.data());
  die("exec", strerror(errno));
  // [[noreturn]] does not work on lambdas...
  _Exit(1);
}

bool Unix::Wait(ExecutionInfo* info, std::string* error_msg) {
  close(pipe_fds_[1]);
  int error_len = 0;
  if (read(pipe_fds_[0], &error_len, sizeof(error_len)) == sizeof(error_len)) {
    char error[PIPE_BUF] = {};
    read(pipe_fds_[0], error, error_len);
    *error_msg = error;
    return false;
  }
  close(pipe_fds_[0]);

  auto program_start = std::chrono::high_resolution_clock::now();
  auto elapsed_millis = [&program_start]() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::high_resolution_clock::now() - program_start)
        .count();
  };

  // TODO(veluca): wait4 is marked as obsolete and replaced by waitpid, but
  // waitpid does not return the resource usage of the child. Moreover,
  // getrusage() may not work for that purpose as other children may have exited
  // in the meantime.
  int child_status = 0;
  bool has_exited = false;
  struct rusage rusage;
  while (elapsed_millis() < options_->wall_limit_millis) {
    int ret = wait4(child_pid_, &child_status, WNOHANG, &rusage);
    if (ret == -1) {
      // This should never happen.
      perror("wait4");
      exit(1);
    }
    if (ret == child_pid_) {
      has_exited = true;
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  if (!has_exited) {
    if (options_->wall_limit_millis) {
      if (kill(child_pid_, SIGKILL) == -1) {
        // This should never happen.
        perror("kill");
        exit(1);
      }
    }
    if (wait4(child_pid_, &child_status, 0, &rusage) != child_pid_) {
      // This should never happen.
      perror("wait4");
      exit(1);
    }
  }
  info->status_code = WIFEXITED(child_status) ? WEXITSTATUS(child_status) : 0;
  info->signal = WIFSIGNALED(child_status) ? WTERMSIG(child_status) : 0;
  info->wall_time_millis = elapsed_millis();
  info->cpu_time_millis =
      (int64_t)rusage.ru_utime.tv_sec * 1000 + rusage.ru_utime.tv_usec / 1000;
  info->sys_time_millis =
      (int64_t)rusage.ru_stime.tv_sec * 1000 + rusage.ru_stime.tv_usec / 1000;

  // On MAC OS X, rusage.ru_maxrss is in bytes.
#ifndef __APPLE__
  info->memory_usage_kb = rusage.ru_maxrss;
#else
  info->memory_usage_kb = rusage.ru_maxrss / 1024;
#endif

  OnFinish(info);
  return true;
}

namespace {
Sandbox::Register<Unix> r;
}  // namespace

}  // namespace sandbox
