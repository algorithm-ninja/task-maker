#include "manager/terry_generation.hpp"

namespace manager {
TerryGeneration::TerryGeneration(EventQueue* queue, core::Core* core,
                                 const proto::TerryTask& task,
                                 proto::CacheMode /*cache_mode*/,
                                 const std::string& /*executor*/,
                                 bool keep_sandbox) {
  generator_ = SourceFile::FromProto(queue, core, task.generator(), {}, true,
                                     keep_sandbox);
  checker_ = SourceFile::FromProto(queue, core, task.checker(), {}, true,
                                   keep_sandbox);
  if (task.has_validator())
    validator_ = SourceFile::FromProto(queue, core, task.validator(), {}, true,
                                       keep_sandbox);
}
}  // namespace manager