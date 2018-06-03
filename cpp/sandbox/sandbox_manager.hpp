#ifndef SANDBOX_SANDBOX_MANAGER_HPP
#define SANDBOX_SANDBOX_MANAGER_HPP
#include "sandbox/sandbox.hpp"

namespace sandbox {

class SandboxManager {
 public:
  static void Start();
  static void Stop();
  static void ChangeNumBoxes(size_t num);
  static bool Execute(const ExecutionOptions& options, ExecutionInfo* info,
                      std::string* error_msg);
};

}  // namespace sandbox
#endif
