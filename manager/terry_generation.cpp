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

void TerryGeneration::WriteGenerator(
    const proto::EvaluateTerryTaskRequest& request) {
  if (request.write_generator_to().empty())
    throw std::range_error("write_generator_to not provided");
  generator_->WriteTo(request.write_generator_to(), true, true);
}

void TerryGeneration::WriteValidator(
    const proto::EvaluateTerryTaskRequest& request) {
  if (request.write_validator_to().empty())
    throw std::range_error("write_validator_to not provided");
  validator_->WriteTo(request.write_validator_to(), true, true);
}

void TerryGeneration::WriteChecker(
    const proto::EvaluateTerryTaskRequest& request) {
  if (request.write_checker_to().empty())
    throw std::range_error("write_checker_to not provided");
  checker_->WriteTo(request.write_checker_to(), true, true);
}

}  // namespace manager