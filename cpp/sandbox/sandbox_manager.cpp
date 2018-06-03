#include "sandbox/sandbox_manager.hpp"
#include "sandbox/sandbox.hpp"

namespace sandbox {
void SandboxManager::Start() {
  //
}
bool SandboxManager::Execute(const ExecutionOptions& options,
                             ExecutionInfo* info, std::string* error_msg) {
  std::unique_ptr<sandbox::Sandbox> sb = Sandbox::Create();
  return sb->Execute(options, info, error_msg);
}

void SandboxManager::ResponseReceiver() {
  //
}
void SandboxManager::Manager() {
  //
}
void SandboxManager::Sandbox() {
  //
}
}  // namespace sandbox
