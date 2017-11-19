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
  int32_t stdin_fd = -1;
  int32_t stdout_fd = -1;
  int32_t stderr_fd = -1;
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
class Sandbox {
 public:
  using create_t = std::function<Sandbox*()>;
  using score_t = std::function<int()>;
  static std::unique_ptr<Sandbox> Create();
  virtual ExecutionInfo Execute(const ExecutionOptions& options);

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
