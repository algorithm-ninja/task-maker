#include "sandbox/unix_dummy.hpp"

namespace sandbox {

ExecutionInfo UnixDummy::Execute(const ExecutionOptions& options) {
  // TODO(veluca): implement this for real.
  ExecutionInfo info;
  info.status_code = -1;
  return info;
}

namespace {
Sandbox::Register<UnixDummy> r;
}  // namespace

}  // namespace sandbox
