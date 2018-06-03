#ifndef SANDBOX_ECHO_HPP
#define SANDBOX_ECHO_HPP
#include "sandbox/sandbox.hpp"

namespace sandbox {

class Echo : public Sandbox {
 public:
  static Sandbox* Create() { return new Echo(); }
  static int Score() { return 1; }

 protected:
  bool ExecuteInternal(const ExecutionOptions& options, ExecutionInfo* info,
                       std::string* error_msg) override;

 private:
  Echo() = default;
};

}  // namespace sandbox
#endif
