#ifndef SANDBOX_ECHO_HPP
#define SANDBOX_ECHO_HPP
#include "sandbox/sandbox.hpp"

namespace sandbox {

class Echo : public Sandbox {
 public:
  bool Execute(const ExecutionOptions& options, ExecutionInfo* info,
               std::string* error_msg) override;
  static Sandbox* Create() { return new Echo(); }
  static int Score() { return 1; }

 private:
  Echo() = default;
};

}  // namespace sandbox
#endif
