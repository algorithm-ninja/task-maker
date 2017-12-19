#include "sandbox/unix.hpp"

#include <atomic>
#include <chrono>
#include <thread>

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <spawn.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {
char* mystrerror(int err, char* buf, size_t buf_size) {
#ifdef _GNU_SOURCE
  return strerror_r(err, buf, buf_size);
#else
  strerror_r(err, buf, buf_size);
  return buf;
#endif
}

int GetProcessMemoryUsageFromProc(pid_t pid, long long* memory_usage_kb) {
  int fd = open(("/proc/" + std::to_string(pid) + "/statm").c_str(),
                O_RDONLY | O_CLOEXEC);
  if (fd == -1) return fd;
  char buf[64 * 1024] = {};
  int num_read = 0;
  int cur = 0;
  do {
    cur = read(fd, buf + num_read, 64 * 1024 - num_read);
    if (cur < 0) {
      close(fd);
      return -1;
    }
    num_read += cur;
  } while (cur > 0);
  close(fd);
  sscanf(buf, "%lld", memory_usage_kb);
  *memory_usage_kb *= 4;
  return 0;
}

int GetProcessMemoryUsage(pid_t pid, long long* memory_usage_kb) {
#ifndef __APPLE__
  return GetProcessMemoryUsageFromProc(pid, memory_usage_kb);
#else
  if (GetProcessMemoryUsageFromProc(pid, memory_usage_kb) == 0) return 0;
  int pipe_fds[2];
  if (pipe(pipe_fds) == -1) return errno;
  posix_spawn_file_actions_t actions;
  int ret = posix_spawn_file_actions_init(&actions);
  if (ret != 0) return ret;
  ret = posix_spawn_file_actions_addclose(&actions, pipe_fds[0]);
  if (ret != 0) return ret;
  ret = posix_spawn_file_actions_addclose(&actions, STDIN_FILENO);
  if (ret != 0) return ret;
  ret = posix_spawn_file_actions_adddup2(&actions, pipe_fds[1], STDOUT_FILENO);
  if (ret != 0) return ret;
  ret = posix_spawn_file_actions_addclose(&actions, pipe_fds[1]);
  if (ret != 0) return ret;
  std::vector<std::unique_ptr<char[]>> args;
  std::vector<char*> args_list;
  auto add_arg = [&args, &args_list](const char* a) {
    args.emplace_back(strdup(a));
    args_list.push_back(args.back().get());
  };
  add_arg("ps");
  add_arg("-o");
  add_arg("vsz=");
  add_arg(std::to_string(pid).c_str());
  args_list.push_back(nullptr);

  char** environ = {nullptr};

  int child_pid = 0;
  ret = posix_spawnp(&child_pid, "ps", &actions, nullptr, args_list.data(),
                     environ);
  close(pipe_fds[1]);
  if (ret != 0) {
    close(pipe_fds[0]);
    return ret;
  }
  int child_status = 0;
  if (waitpid(child_pid, &child_status, 0) == -1) {
    close(pipe_fds[0]);
    return errno;
  }
  if (child_status != 0) {
    close(pipe_fds[0]);
    *memory_usage_kb = 0;
    return 0;
  }
  char memory_usage_buf[1024] = {};
  if (read(pipe_fds[0], memory_usage_buf, 1024) == -1) {
    close(pipe_fds[0]);
    *memory_usage_kb = 0;
    return 0;
  }
  close(pipe_fds[0]);
  if (sscanf(memory_usage_buf, "%lld", memory_usage_kb) != 1) {
    *memory_usage_kb = 0;
  }
  return 0;
#endif
}
}  // namespace

namespace sandbox {

static const constexpr size_t kStrErrorBufSize = 2048;

bool Unix::MakeImmutable(const std::string& input_file,
                         std::string* error_msg) {
  char buf[kStrErrorBufSize] = {};
  if (chmod(input_file.c_str(), S_IRUSR) == -1) {
    *error_msg = "chmod: ";
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);
    return false;
  }
  return true;
}

bool Unix::PrepareForExecution(const std::string& executable,
                               std::string* error_msg) {
  char buf[kStrErrorBufSize] = {};
  if (chmod(executable.c_str(), S_IRUSR | S_IXUSR) == -1) {
    *error_msg = "chmod: ";
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);
    return false;
  }
  return true;
}

bool Unix::Execute(const ExecutionOptions& options, ExecutionInfo* info,
                   std::string* error_msg) {
  options_ = &options;
  if (!Setup(error_msg)) return false;
  if (!DoFork(error_msg)) return false;
  if (!Wait(info, error_msg)) return false;
  return true;
}

bool Unix::Setup(std::string* error_msg) {
  char buf[kStrErrorBufSize] = {};
  if (pipe(pipe_fds_) == -1) {
    *error_msg = "pipe2: ";
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);
    return false;
  }
  if (fcntl(pipe_fds_[0], F_SETFD, FD_CLOEXEC) == -1 ||
      fcntl(pipe_fds_[1], F_SETFD, FD_CLOEXEC) == -1) {
    *error_msg = "fcntl: ";
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);
    return false;
  }
  return true;
}

bool Unix::DoFork(std::string* error_msg) {
  char buf[kStrErrorBufSize] = {};
  int fork_result = fork();
  if (fork_result == -1) {
    *error_msg = "fork: ";
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);
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
  close(pipe_fds_[0]);
  auto die2 = [this](const char* prefix, const char* err) {
    fprintf(stdout, "%s\n", err);
    char buf[kStrErrorBufSize + 64 + 2] = {};
    strncat(buf, prefix, 64);
    strncat(buf, ": ", 2);
    strncat(buf, err, kStrErrorBufSize);
    int len = strlen(buf);
    write(pipe_fds_[1], &len, sizeof(len));
    write(pipe_fds_[1], buf, len);
    close(pipe_fds_[1]);
    _Exit(1);
  };

  auto die = [&die2](const char* prefix, int err) {
    char buf[kStrErrorBufSize] = {};
    die2(prefix, mystrerror(err, buf, kStrErrorBufSize));
  };

  // Change process group, so that we do not receive Ctrl-Cs in the terminal.
  if (setsid() == -1) die("setsid", errno);

  int stdin_fd = -1;
  int stdout_fd = -1;
  int stderr_fd = -1;
  if (options_->stdin_file != "") {
    stdin_fd = open(options_->stdin_file.c_str(), O_RDONLY);
    if (stdin_fd == -1) die("open", errno);
  }
  if (options_->stdout_file != "") {
    stdout_fd = creat(options_->stdout_file.c_str(), S_IRUSR | S_IWUSR);
    if (stdout_fd == -1) die("creat", errno);
  }
  if (options_->stderr_file != "") {
    stderr_fd = creat(options_->stderr_file.c_str(), S_IRUSR | S_IWUSR);
    if (stderr_fd == -1) die("creat", errno);
  }

  if (chdir(options_->root.c_str()) == -1) {
    die("chdir", errno);
  }

  // TODO(veluca): do not use dynamic memory allocation here.
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
#define DUP(field, fd)                          \
  if (field##_fd != -1) {                       \
    int ret = dup2(field##_fd, fd);             \
    if (ret == -1) die("redir " #field, errno); \
  }
  if (stdin_fd) {
    DUP(stdin, STDIN_FILENO);
  } else if (close(STDIN_FILENO) == -1) {
    die("close", errno);
  }
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
        die("setrlim " #res, errno);            \
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

  char buf[kStrErrorBufSize] = {};
  if (!OnChild(buf, kStrErrorBufSize)) {
    die2("OnChild", buf);
  }
  int count = 0;
  do {
    execv(options_->executable.c_str(), args.data());
    usleep(100);
    // We try at most 16 times to avoid livelocks (which should not be possible,
    // but better safe than sorry).
  } while (errno == ETXTBSY && count++ < 16);
  die("exec", errno);
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
  std::atomic<long long> memory_usage{0};
  bool done = false;
  std::thread memory_watcher(
      [&memory_usage, &done](int pid) {
        while (!done) {
          long long mem;
          if (GetProcessMemoryUsage(pid, &mem) == 0) {
            if (mem > memory_usage) memory_usage = mem;
          }
          std::this_thread::sleep_for(std::chrono::microseconds(100));
        }
      },
      child_pid_);

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
    if (options_->memory_limit_kb && memory_usage > options_->memory_limit_kb)
      break;
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
  done = true;
  memory_watcher.join();
  info->memory_usage_kb = memory_usage;
  info->status_code = WIFEXITED(child_status) ? WEXITSTATUS(child_status) : 0;
  info->signal = WIFSIGNALED(child_status) ? WTERMSIG(child_status) : 0;
  info->wall_time_millis = elapsed_millis();
  info->cpu_time_millis =
      (int64_t)rusage.ru_utime.tv_sec * 1000 + rusage.ru_utime.tv_usec / 1000;
  info->sys_time_millis =
      (int64_t)rusage.ru_stime.tv_sec * 1000 + rusage.ru_stime.tv_usec / 1000;

  OnFinish(info);
  return true;
}

namespace {
Sandbox::Register<Unix> r;
}  // namespace

}  // namespace sandbox
