#ifndef SANDBOX_SANDBOX_MANAGER_HPP
#define SANDBOX_SANDBOX_MANAGER_HPP
#include "sandbox/sandbox.hpp"

namespace sandbox {

class SandboxManager {
 public:
  static void Start();
  static bool Execute(const ExecutionOptions& options, ExecutionInfo* info,
                      std::string* error_msg);

 private:
  static void ResponseReceiver();
  static void Manager();
  static void Sandbox();
};

}  // namespace sandbox
#endif
