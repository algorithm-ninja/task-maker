#include "manager/terry_evaluation.hpp"
#include "glog/logging.h"
#include "nlohmann/json.hpp"

namespace manager {
TerryEvaluation::TerryEvaluation(EventQueue* queue, core::Core* core,
                                 TerryGeneration* generation,
                                 proto::TerryTask task,
                                 proto::CacheMode cache_mode,
                                 std::string executor, bool keep_sandbox)
    : queue_(queue),
      core_(core),
      generation_(generation),
      task_(std::move(task)),
      cache_mode_(cache_mode),
      executor_(std::move(executor)),
      keep_sandbox_(keep_sandbox) {}

void TerryEvaluation::Evaluate(SourceFile* solution) {
  std::string name = solution->Name();
  std::string seed = "42";  // TODO(edomora97) generate seed
  LOG(INFO) << "Evaluating " << name << " with seed " << seed;
  core::Execution* generation = generation_->GetGenerator()->execute(
      "Generation of input for solution " + name + " with seed " + seed,
      {seed, "0"}, keep_sandbox_);
  core::FileID* input = generation->Stdout();
  if (cache_mode_ == proto::GENERATION || cache_mode_ == proto::ALL)
    generation->SetCachingMode(core::Execution::CachingMode::ALWAYS);
  else
    generation->SetCachingMode(core::Execution::CachingMode::NEVER);
  generation->SetExecutor(executor_);
  generation->SetCallback([this, name](const core::TaskStatus& status) -> bool {
    if (status.type == core::TaskStatus::FILE_LOAD)
      return !(status.event == core::TaskStatus::FAILURE);
    if (status.event == core::TaskStatus::START) queue_->TerryGenerating(name);
    if (status.event == core::TaskStatus::SUCCESS) {
      auto exec = status.execution_info;
      if (exec->Success()) {
        queue_->TerryGenerated(name);
      } else {
        queue_->TerryGenerationFailure(
            name,
            status.message + "\n" + exec->Stderr()->Contents(1024 * 1024));
        return false;
      }
    }
    if (status.event == core::TaskStatus::FAILURE) {
      queue_->FatalError(status.message + ": " +
                         status.execution_info->Message());
      return false;
    }
    return true;
  });

  if (task_.has_validator()) {
    core::Execution* validation = generation_->GetValidator()->execute(
        "Validation of input for solution " + name, {"0"}, keep_sandbox_);
    validation->Stdin(input);
    if (cache_mode_ == proto::GENERATION || cache_mode_ == proto::ALL)
      validation->SetCachingMode(core::Execution::CachingMode::ALWAYS);
    else
      validation->SetCachingMode(core::Execution::CachingMode::NEVER);
    validation->SetExecutor(executor_);
    validation->SetCallback([this,
                             name](const core::TaskStatus& status) -> bool {
      if (status.type == core::TaskStatus::FILE_LOAD)
        return !(status.event == core::TaskStatus::FAILURE);
      if (status.event == core::TaskStatus::START)
        queue_->TerryValidating(name);
      if (status.event == core::TaskStatus::SUCCESS) {
        auto exec = status.execution_info;
        if (exec->Success()) {
          queue_->TerryValidated(name);
        } else {
          queue_->TerryGenerationFailure(
              name,
              status.message + "\n" + exec->Stderr()->Contents(1024 * 1024));
          return false;
        }
      }
      if (status.event == core::TaskStatus::FAILURE) {
        queue_->FatalError(status.message + ": " +
                           status.execution_info->Message());
        return false;
      }
      return true;
    });
  }

  core::Execution* execution =
      solution->execute("Testing solution " + name, {}, keep_sandbox_);
  execution->Stdin(input);
  core::FileID* output = execution->Stdout();
  if (cache_mode_ == proto::ALL)
    execution->SetCachingMode(core::Execution::CachingMode::ALWAYS);
  else
    execution->SetCachingMode(core::Execution::CachingMode::NEVER);
  execution->SetExecutor(executor_);
  execution->SetCallback([this, name](const core::TaskStatus& status) -> bool {
    if (status.type == core::TaskStatus::FILE_LOAD)
      return !(status.event == core::TaskStatus::FAILURE);
    if (status.event == core::TaskStatus::START) queue_->TerryEvaluating(name);
    if (status.event == core::TaskStatus::SUCCESS) {
      auto exec = status.execution_info;
      if (exec->Success()) {
        queue_->TerryEvaluated(name);
      } else {
        queue_->TerryEvaluationFailure(
            name,
            status.message + "\n" + exec->Stderr()->Contents(1024 * 1024));
      }
    }
    if (status.event == core::TaskStatus::FAILURE) {
      queue_->FatalError(status.message + ": " +
                         status.execution_info->Message());
      return false;
    }
    return true;
  });

  core::Execution* checker =
      generation_->GetChecker()->execute("Checking output of solution " + name,
                                         {"input", "output"}, keep_sandbox_);
  checker->Input("input", input);
  checker->Input("output", output);
  if (cache_mode_ == proto::ALL)
    checker->SetCachingMode(core::Execution::CachingMode::ALWAYS);
  else
    checker->SetCachingMode(core::Execution::CachingMode::NEVER);
  checker->SetExecutor(executor_);
  core::FileID* checker_results = checker->Stdout();
  checker->SetCallback(
      [this, name, checker_results](const core::TaskStatus& status) -> bool {
        if (status.type == core::TaskStatus::FILE_LOAD)
          return !(status.event == core::TaskStatus::FAILURE);
        if (status.event == core::TaskStatus::START)
          queue_->TerryChecking(name);
        if (status.event == core::TaskStatus::SUCCESS) {
          auto exec = status.execution_info;
          if (exec->Success()) {
            auto checker_json =
                nlohmann::json::parse(checker_results->Contents(1024 * 1024));
            proto::TerryEvaluationResult result;
            result.set_score(checker_json["score"]);
            queue_->TerryChecked(name, std::move(result));
          } else {
            queue_->TerryCheckingFailure(
                name,
                status.message + "\n" + exec->Stderr()->Contents(1024 * 1024));
            return false;
          }
        }
        if (status.event == core::TaskStatus::FAILURE) {
          queue_->FatalError(status.message + ": " +
                             status.execution_info->Message());
          return false;
        }
        return true;
      });
}
}  // namespace manager