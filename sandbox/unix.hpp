#ifndef SANDBOX_UNIX_HPP
#define SANDBOX_UNIX_HPP
#include "sandbox/sandbox.hpp"

namespace sandbox {

// Base class for sandboxes for UNIX-like systems.
class Unix : public Sandbox {
 public:
  bool PrepareForExecution(const std::string& executable,
                           std::string* error_msg) override;
  bool MakeImmutable(const std::string& input_file,
                     std::string* error_msg) override;
  bool Execute(const ExecutionOptions& options, ExecutionInfo* info,
               std::string* error_msg) override;
  static Sandbox* Create() { return new Unix(); }
  static int Score() { return 2; }

 protected:
  Unix() = default;

  // Executed before creating the child process. Returns false and sets
  // error_msg if setup fails.
  bool Setup(std::string* error_msg);

  // Hook that is executed at the end of PreFork.
  virtual bool OnSetup(std::string* error_msg) { return true; }

  // Creates a child process and saves its PID in child_pid_. The child process
  // should execute Child and must not return.
  virtual bool DoFork(std::string* error_msg);

  // Function that is executed in the child process.
  [[noreturn]] void Child();

  // Hook that is executed just before exec. Returns false if something went
  // wrong and exec should not be called. The error_msg string must not be
  // longer then buflen characters. This function must not use dynamic memory
  // allocation.
  virtual bool OnChild(char* error_msg, size_t buflen) { return true; }

  // Waits for the termination of the child, possibly killing it if it exceeds
  // the provided wall time limit.
  bool Wait(ExecutionInfo* info, std::string* error_msg);

  // Executed when the child program exits. May change the execution info with
  // "better" values, or perform clean up.
  virtual void OnFinish(ExecutionInfo* info) {}

  int pipe_fds_[2] = {};
  int child_pid_ = 0;
  const ExecutionOptions* options_ = nullptr;
};

}  // namespace sandbox
#endif
