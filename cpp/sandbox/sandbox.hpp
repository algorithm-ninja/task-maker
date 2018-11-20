#ifndef SANDBOX_SANDBOX_HPP
#define SANDBOX_SANDBOX_HPP

#include <cstring>
#include <functional>
#include <memory>
#include <string>
#include <vector>
#include "util/file.hpp"

namespace sandbox {

// Settings to execute the program in the sandbox.
struct ExecutionOptions {
  static const constexpr size_t str_len = 1024;
  static const constexpr size_t narg = 16;

  // Optional values
  int64_t cpu_limit_millis = 0;
  int64_t wall_limit_millis = 0;
  int64_t memory_limit_kb = 0;
  int32_t max_procs = 0;
  int32_t max_files = 0;
  int64_t max_file_size_kb = 0;
  int64_t max_mlock_kb = 0;
  int64_t max_stack_kb = 0;

  char stdin_file[str_len] = {};
  char stdout_file[str_len] = {};
  char stderr_file[str_len] = {};
  char args[narg][str_len] = {};

  // Required values
  char root[str_len] = {};
  char executable[str_len] = {};
  bool prepare_executable = false;
  ExecutionOptions(const std::string& root_, const std::string& executable_) {
    memset(this, 0, sizeof(*this));
    stringcpy(root, root_);
    stringcpy(executable, executable_);
    strncpy(&args[0][0], executable, str_len);
  }
  template <typename T>
  void SetArgs(const T& a_) {
    size_t i = 1;
    for (const std::string& s : a_) {
      stringcpy(&args[i][0], s);
      if (i++ >= narg) throw std::runtime_error("Too many arguments");
    }
  }
  void SetArgs(const std::initializer_list<const char*>& a_) {
    size_t i = 1;
    for (const char* s : a_) {
      if (strlen(s) >= str_len) throw std::runtime_error("string too long");
      strncpy(&args[i][0], s, str_len);
      if (i++ >= narg) throw std::runtime_error("Too many arguments");
    }
  }

  static void stringcpy(char* dst, const std::string& s) {
    if (s.size() >= str_len) throw std::runtime_error("string too long");
    strncpy(dst, s.c_str(), str_len - 1);
  }
};

// Results of the execution.
struct ExecutionInfo {
  int64_t cpu_time_millis = 0;
  int64_t sys_time_millis = 0;
  int64_t wall_time_millis = 0;
  int64_t memory_usage_kb = 0;
  int32_t status_code = 0;
  int32_t signal = 0;
  bool killed = false;
  char message[8192] = {};
};

// Sandbox interface. Implementations need to register themselves by creating a
// global object of type Sandbox::Register<SandboxImpl> and should define the
// Create and Score static functions. Create should return a pointer to a newly
// allocated instance of the given implementation, while Score should return a
// value that defines how "good" that sandbox is: negative if the sandbox
// should not/cannot be used in the current configuration, positive otherwise
// (a bigger value means a better sandbox).
// Registering a sandbox is not thread-safe and should be done before any
// threads are created.
class Sandbox {
 public:
  using create_t = std::function<Sandbox*()>;
  using score_t = std::function<int()>;
  static std::unique_ptr<Sandbox> Create();

  // Runs the specified command. Returns true if the program was started,
  // and sets fields in info. Otherwise, returns false and sets error_msg.
  // Implementations of this function may not be thread safe.
  bool Execute(const ExecutionOptions& options, ExecutionInfo* info,
               std::string* error_msg) {
    if (options.prepare_executable) {
      if (!PrepareForExecution(
              util::File::JoinPath(options.root, options.executable),
              error_msg)) {
        return false;
      }
    }
    return ExecuteInternal(options, info, error_msg);
  }

  // Constructor and destructors
  virtual ~Sandbox() = default;
  Sandbox() = default;
  Sandbox(const Sandbox&) = delete;
  Sandbox(Sandbox&&) = delete;
  Sandbox& operator=(const Sandbox&) = delete;
  Sandbox& operator=(Sandbox&&) = delete;

  template <typename T>
  class Register {
   public:
    Register() { Sandbox::Register_(&T::Create, &T::Score); }
  };

 protected:
  virtual bool ExecuteInternal(const ExecutionOptions& options,
                               ExecutionInfo* info, std::string* error_msg) = 0;

  // Prepares a newly-created file for execution. Returns false on error,
  // and sets error_msg.
  virtual bool PrepareForExecution(const std::string& /*executable*/,
                                   std::string* /*error_msg*/) {
    return true;
  }

 private:
  using store_t = std::vector<std::pair<create_t, score_t>>;
  static store_t* Boxes_();
  static void Register_(create_t, score_t);
  template <typename T>
  friend class Register;
};

}  // namespace sandbox

#endif
