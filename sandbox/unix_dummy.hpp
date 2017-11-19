#ifndef SANDBOX_UNIX_DUMMY_HPP
#define SANDBOX_UNIX_DUMMY_HPP
#include "sandbox/sandbox.hpp"

namespace sandbox {

class UnixDummy : public Sandbox {
 public:
  ExecutionInfo Execute(const ExecutionOptions& options) override;
  static Sandbox* Create() { return new UnixDummy(); }
  static int Score() { return 2; }

 private:
  UnixDummy() = default;
};

}  // namespace sandbox
#endif
