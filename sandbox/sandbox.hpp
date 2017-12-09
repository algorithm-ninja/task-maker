#ifndef SANDBOX_SANDBOX_HPP
#define SANDBOX_SANDBOX_HPP

#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace sandbox {

// Settings to execute the program in the sandbox.
struct ExecutionOptions {
  // Optional values
  int64_t cpu_limit_millis = 0;
  int64_t wall_limit_millis = 0;
  int64_t memory_limit_kb = 0;
  int32_t max_procs = 0;
  int32_t max_files = 0;
  int64_t max_file_size_kb = 0;
  int64_t max_mlock_kb = 0;
  int64_t max_stack_kb = 0;

  std::string stdin_file = "";
  std::string stdout_file = "";
  std::string stderr_file = "";
  std::vector<std::string> args;

  // Required values
  std::string root = "";
  std::string executable = "";
  ExecutionOptions(std::string root, std::string executable)
      : root(std::move(root)), executable(std::move(executable)) {}
};

// Results of the execution.
struct ExecutionInfo {
  int64_t cpu_time_millis = 0;
  int64_t sys_time_millis = 0;
  int64_t wall_time_millis = 0;
  int64_t memory_usage_kb = 0;
  int32_t status_code = 0;
  int32_t signal = 0;
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

  // Prepares a newly-created file for execution. Returns false on error,
  // and sets error_msg.
  virtual bool PrepareForExecution(const std::string& executable,
                                   std::string* error_msg) {
    return true;
  }

  // Runs the specified command. Returns true if the program was started,
  // and sets fields in info. Otherwise, returns false and sets error_msg.
  // Implementations of this function may not be thread safe.
  virtual bool Execute(const ExecutionOptions& options, ExecutionInfo* info,
                       std::string* error_msg) = 0;

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

 private:
  using store_t = std::vector<std::pair<create_t, score_t>>;
  static store_t* Boxes_();
  static void Register_(create_t, score_t);
  template <typename T>
  friend class Register;
};

}  // namespace sandbox

#endif
