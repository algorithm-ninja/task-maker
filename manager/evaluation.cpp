#include "manager/evaluation.hpp"

#include "core/execution.hpp"
#include "core/file_id.hpp"

namespace manager {

Evaluation::Evaluation(EventQueue* queue, core::Core* core,
                       const Generation& generation, const proto::Task& task,
                       bool exclusive, proto::CacheMode cache_mode,
                       const std::string& executor) {
  // ...
}

void Evaluation::Evaluate(SourceFile* solution) {
  // ...
}
}  // namespace manager
