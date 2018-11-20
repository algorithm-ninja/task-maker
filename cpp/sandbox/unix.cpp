#include "sandbox/unix.hpp"

#include <fcntl.h>
#include <spawn.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cinttypes>
#include <climits>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <thread>

#include <kj/debug.h>

namespace {
char* mystrerror(int err, char* buf, size_t buf_size) {
#ifdef _GNU_SOURCE
  return strerror_r(err, buf, buf_size);
#else
  strerror_r(err, buf, buf_size);
  return buf;
#endif
}

#ifdef __APPLE__
int GetProcessMemoryUsageFromProc(pid_t pid, int64_t* memory_usage_kb) {
  int fd = open(("/proc/" + std::to_string(pid) + "/statm").c_str(),  // NOLINT
                O_RDONLY | O_CLOEXEC);
  if (fd == -1) return -1;
  char buf[64 * 1024] = {};
  size_t num_read = 0;
  ssize_t cur = 0;
  do {
    cur = read(fd, buf + num_read, 64 * 1024 - num_read);  // NOLINT
    if (cur < 0) {
      close(fd);
      return -1;
    }
    num_read += cur;
  } while (cur > 0);
  close(fd);
  if (sscanf(buf, "%" SCNd64, memory_usage_kb) != 1) {            // NOLINT
    fprintf(stderr, "Unable to get memory usage from /proc: %s",  // NOLINT
            buf);                                                 // NOLINT
    exit(1);
  }
  *memory_usage_kb *= 4;
  return 0;
}

int GetProcessMemoryUsage(pid_t pid, int64_t* memory_usage_kb) {
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
  std::vector<std::vector<char> > args;
  auto add_arg = [&args](std::string s) {
    std::vector<char> arg(s.size() + 1);
    std::copy(s.begin(), s.end(), arg.begin());
    arg.back() = '\0';
    args.push_back(std::move(arg));
  };
  add_arg("ps");
  add_arg("-o");
  add_arg("rss=");
  add_arg(std::to_string(pid));

  std::vector<char*> args_list(args.size() + 1);
  for (size_t i = 0; i < args.size(); i++) args_list[i] = args[i].data();
  args_list.back() = nullptr;

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
  if (sscanf(memory_usage_buf, "%" SCNd64, memory_usage_kb) != 1) {
    *memory_usage_kb = 0;
  }
  return 0;
}
#endif
}  // namespace

namespace sandbox {

static const constexpr size_t kStrErrorBufSize = 2048;

bool Unix::PrepareForExecution(const std::string& executable,
                               std::string* error_msg) {
  if (chmod(executable.c_str(), S_IRUSR | S_IXUSR) == -1) {
    *error_msg = "chmod: ";
    char buf[kStrErrorBufSize] = {};
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);  // NOLINT
    return false;
  }
  return true;
}

bool Unix::ExecuteInternal(const ExecutionOptions& options, ExecutionInfo* info,
                           std::string* error_msg) {
  options_ = &options;
  if (!Setup(error_msg)) return false;
  if (!DoFork(error_msg)) return false;
  if (!Wait(info, error_msg)) return false;
  return true;
}

bool Unix::Setup(std::string* error_msg) {
  char buf[kStrErrorBufSize] = {};
  if (pipe(pipe_fds_) == -1) {  // NOLINT
    *error_msg = "pipe2: ";
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);  // NOLINT
    return false;
  }
  if (fcntl(pipe_fds_[0], F_SETFD, FD_CLOEXEC) == -1 ||  // NOLINT
      fcntl(pipe_fds_[1], F_SETFD, FD_CLOEXEC) == -1) {  // NOLINT
    *error_msg = "fcntl: ";
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);  // NOLINT
    return false;
  }
  return true;
}

bool Unix::DoFork(std::string* error_msg) {
  int fork_result = fork();
  if (fork_result == -1) {
    *error_msg = "fork: ";
    char buf[kStrErrorBufSize] = {};
    *error_msg += mystrerror(errno, buf, kStrErrorBufSize);  // NOLINT
    return false;
  }
  if (fork_result != 0) {
    child_pid_ = fork_result;
    return true;
  }
  Child();
}

void Unix::Child() {
  close(pipe_fds_[0]);
  auto die2 = [this](const char* prefix, const char* err) {
    fprintf(stdout, "%s\n", err);  // NOLINT
    char buf[kStrErrorBufSize + 64 + 3 + 1] = {};
    strncat(buf, prefix, 64);             // NOLINT
    strncat(buf, ": ", 3);                // NOLINT
    strncat(buf, err, kStrErrorBufSize);  // NOLINT
    ssize_t len = strlen(buf);            // NOLINT
    KJ_SYSCALL(write(pipe_fds_[1], &len, sizeof(len)), "Failed to write to fd");
    KJ_SYSCALL(write(pipe_fds_[1], buf, len), "Failed to write to fd");
    close(pipe_fds_[1]);
    _Exit(1);
  };

  auto die = [&die2](const char* prefix, int err) {
    char buf[kStrErrorBufSize] = {};
    die2(prefix, mystrerror(err, buf, kStrErrorBufSize));  // NOLINT
  };

  // Change process group, so that we do not receive Ctrl-Cs in the terminal.
  if (setsid() == -1) die("setsid", errno);

  int stdin_fd = -1;
  int stdout_fd = -1;
  int stderr_fd = -1;
  // fprintf(stderr, "%s\n", options_->stdin_file);
  if (options_->stdin_file[0]) {
    stdin_fd = open(options_->stdin_file, O_RDONLY | O_CLOEXEC);
    if (stdin_fd == -1) die("open", errno);
  }
  if (options_->stdout_file[0]) {
    stdout_fd =
        open(options_->stdout_file, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC,
             S_IRUSR | S_IWUSR);
    if (stdout_fd == -1) die("open", errno);
  }
  if (options_->stderr_file[0]) {
    stderr_fd =
        open(options_->stderr_file, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC,
             S_IRUSR | S_IWUSR);
    if (stderr_fd == -1) die("open", errno);
  }

  if (chdir(options_->root) == -1) {
    die("chdir", errno);
  }

  decltype(options_->args) args = {};
  memcpy(args, options_->args, sizeof(args));
  char* argsp[ExecutionOptions::narg + 1] = {};
  size_t narg = 0;
  // NOLINTNEXTLINE
  for (size_t i = 0; i < ExecutionOptions::narg; i++) {
    if (!args[i][0]) break;
    argsp[narg++] = &args[i][0];
  }

  // Handle I/O redirection.
#define DUP(field, fd)                          \
  if (field##_fd != -1) {                       \
    int ret = dup2(field##_fd, fd);             \
    if (ret == -1) die("redir " #field, errno); \
  }
  if (stdin_fd != 0) {
    DUP(stdin, STDIN_FILENO);
  } else if (close(STDIN_FILENO) == -1) {
    die("close", errno);
  }
  DUP(stdout, STDOUT_FILENO);
  DUP(stderr, STDERR_FILENO);
#undef DUP

  // Set resource limits.
  struct rlimit rlim {};
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
  SET_RLIM(CPU, (options_->cpu_limit_millis + 999) / 1000);
  SET_RLIM(FSIZE, options_->max_file_size_kb * 1024);
  SET_RLIM(MEMLOCK, options_->max_mlock_kb * 1024);
  SET_RLIM(NOFILE, options_->max_files);
  SET_RLIM(NPROC, options_->max_procs);
  SET_RLIM(CORE, 0);

  // Setting stack size does not seem to work on MAC.
#ifndef __APPLE__
  SET_RLIM(STACK, options_->max_stack_kb ? options_->max_stack_kb * 1024
                                         : RLIM_INFINITY);
#endif
#undef SET_RLIM

  char buf[kStrErrorBufSize] = {};
  if (!OnChild(buf, kStrErrorBufSize)) {  // NOLINT
    die2("OnChild", buf);                 // NOLINT
  }
  execv(options_->executable, argsp);
  die("exec", errno);
  // [[noreturn]] does not work on lambdas...
  _Exit(1);
}

bool Unix::Wait(ExecutionInfo* info, std::string* error_msg) {
  close(pipe_fds_[1]);
  ssize_t error_len = 0;
  if (read(pipe_fds_[0], &error_len, sizeof(error_len)) == sizeof(error_len)) {
    char error[PIPE_BUF] = {};
    KJ_SYSCALL(read(pipe_fds_[0], error, error_len), "Failed to read from fd");
    *error_msg = error;
    return false;
  }
  std::atomic<int64_t> memory_usage{0};
#ifdef __APPLE__
  bool done = false;
  std::thread memory_watcher(
      [&memory_usage, &done](int pid) {
        while (!done) {
          int64_t mem;
          if (GetProcessMemoryUsage(pid, &mem) == 0) {
            if (mem > memory_usage) memory_usage = mem;
          }
          std::this_thread::sleep_for(std::chrono::microseconds(100));
        }
      },
      child_pid_);
#endif

  close(pipe_fds_[0]);

  auto program_start = std::chrono::high_resolution_clock::now();
  auto elapsed_millis = [&program_start]() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::high_resolution_clock::now() - program_start)
        .count();
  };

  int child_status = 0;
  bool has_exited = false;
  struct rusage rusage {};
  while (!options_->wall_limit_millis ||
         elapsed_millis() < options_->wall_limit_millis) {
    if (options_->memory_limit_kb != 0 &&
        memory_usage > options_->memory_limit_kb) {
      break;
    }
    int ret = waitpid(child_pid_, &child_status, WNOHANG);
    if (ret == -1) {
      // This should never happen.
      perror("waitpid");
      exit(1);
    }
    if (ret == child_pid_) {
      getrusage(RUSAGE_CHILDREN, &rusage);
      has_exited = true;
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  if (!has_exited) {
    if (options_->wall_limit_millis != 0 ||
        (options_->memory_limit_kb != 0 &&
         memory_usage > options_->memory_limit_kb)) {
      if (kill(child_pid_, SIGKILL) == -1) {
        // This should never happen.
        perror("kill");
        exit(1);
      }
    }
    if (waitpid(child_pid_, &child_status, 0) != child_pid_) {
      // This should never happen.
      perror("waitpid");
      exit(1);
    }
    getrusage(RUSAGE_CHILDREN, &rusage);
  }
#ifdef __APPLE__
  done = true;
  memory_watcher.join();
  info->memory_usage_kb = rusage.ru_maxrss / 1024;
#else
  info->memory_usage_kb = rusage.ru_maxrss;
#endif
  info->status_code = WIFEXITED(child_status) ? WEXITSTATUS(child_status) : 0;
  info->signal = WIFSIGNALED(child_status) ? WTERMSIG(child_status) : 0;
  // If the child received a KILL or XCPU signal, assume we killed it
  // because of memory or time limits.
  info->killed = info->signal == SIGKILL || info->signal == SIGXCPU;
  info->wall_time_millis = elapsed_millis();
  info->cpu_time_millis =
      rusage.ru_utime.tv_sec * 1000LL + rusage.ru_utime.tv_usec / 1000;
  info->sys_time_millis =
      rusage.ru_stime.tv_sec * 1000LL + rusage.ru_stime.tv_usec / 1000;
  if (info->signal != 0) {
    strncpy(info->message, strsignal(info->signal), sizeof(info->message));
  } else if (info->status_code != 0) {
    strncpy(info->message, "Non-zero return code", sizeof(info->message));
  }
  OnFinish(info);
  return true;
}

namespace {
Sandbox::Register<Unix> r;  // NOLINT
}  // namespace

}  // namespace sandbox
