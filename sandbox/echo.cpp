#include "sandbox/echo.hpp"

#include <iostream>

namespace sandbox {

ExecutionInfo Echo::Execute(const ExecutionOptions& options) {
  std::cout << "[FAKE] Executing ";
  std::cout << options.executable;
  for (const std::string& arg : options.args) {
    std::cout << " " << arg;
  }
  std::cout << std::endl;
  std::cout << "Inside folder: " << options.root << std::endl;
  return {};
}

namespace {
Sandbox::Register<Echo> r;
}  // namespace

}  // namespace sandbox
