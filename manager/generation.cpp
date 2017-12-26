#include "manager/generation.hpp"

namespace manager {

Generation::Generation(EventQueue* queue, core::Core* core,
                       const proto::Task& task, proto::CacheMode cache_mode,
                       const std::string& executor) {
  // ...
}

// To be called after Core.Run
void Generation::WriteInputs(const std::string& destination) {
  // ...
}
void Generation::WriteOutputs(const std::string& destination) {
  // ...
}
void Generation::WriteChecker(const std::string& destionation) {
  // ...
}
}  // namespace manager
