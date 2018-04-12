#include "manager/terry_format/terry_evaluation.hpp"
#include "glog/logging.h"
#include "nlohmann/json.hpp"

namespace manager {
TerryEvaluation::TerryEvaluation(EventQueue* queue, core::Core* core,
                                 TerryGeneration* generation,
                                 proto::TerryTask task, bool exclusive,
                                 proto::CacheMode cache_mode,
                                 const std::string& executor, bool keep_sandbox)
    : queue_(queue),
      core_(core),
      generation_(generation),
      task_(std::move(task)),
      exclusive_(exclusive),
      cache_mode_(cache_mode),
      executor_(std::move(executor)),
      keep_sandbox_(keep_sandbox) {}

void TerryEvaluation::Evaluate(SourceFile* solution, int64_t seed) {
  std::string name = solution->Name();
  std::string s_seed = std::to_string(seed);
  LOG(INFO) << "Evaluating " << name << " with seed " << seed;

  core::Execution* generation = generation_->GetGenerator()->execute(
      "Generation of input for solution " + name + " with seed " + s_seed,
      {s_seed, "0"}, keep_sandbox_);
  core::Execution* execution =
      solution->execute("Testing solution " + name, {}, keep_sandbox_);
  core::Execution* checker =
      generation_->GetChecker()->execute("Checking output of solution " + name,
                                         {"input", "output"}, keep_sandbox_);
  if (exclusive_) {
    generation->SetExclusive();
    execution->SetExclusive();
    checker->SetExclusive();
  }

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
        queue_->TerryGenerated(name, exec->Cached());
      } else {
        queue_->TerryGenerationFailure(
            name, status.message + "\n" + exec->Stderr()->Contents(1024 * 1024),
            exec->Cached());
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
    // do the execution only after the validation
    execution->Input("dependency_tracker", validation->Stdout());
    validation->SetCallback(
        [this, name](const core::TaskStatus& status) -> bool {
          if (status.type == core::TaskStatus::FILE_LOAD)
            return !(status.event == core::TaskStatus::FAILURE);
          if (status.event == core::TaskStatus::START)
            queue_->TerryValidating(name);
          if (status.event == core::TaskStatus::SUCCESS) {
            auto exec = status.execution_info;
            if (exec->Success()) {
              queue_->TerryValidated(name, exec->Cached());
            } else {
              queue_->TerryGenerationFailure(
                  name,
                  status.message + "\n" + exec->Stderr()->Contents(1024 * 1024),
                  exec->Cached());
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
        queue_->TerryEvaluated(name, exec->Cached());
      } else {
        queue_->TerryEvaluationFailure(
            name, status.message + "\n" + exec->Stderr()->Contents(1024 * 1024),
            exec->Cached());
      }
    }
    if (status.event == core::TaskStatus::FAILURE) {
      queue_->FatalError(status.message + ": " +
                         status.execution_info->Message());
      return false;
    }
    return true;
  });

  checker->Input("input", input);
  checker->Input("output", output);
  if (cache_mode_ == proto::ALL)
    checker->SetCachingMode(core::Execution::CachingMode::ALWAYS);
  else
    checker->SetCachingMode(core::Execution::CachingMode::NEVER);
  checker->SetExecutor(executor_);
  core::FileID* checker_results = checker->Stdout();
  checker->SetCallback([this, name, checker_results, generation, execution,
                        checker,
                        s_seed](const core::TaskStatus& status) -> bool {
    if (status.type == core::TaskStatus::FILE_LOAD)
      return !(status.event == core::TaskStatus::FAILURE);
    if (status.event == core::TaskStatus::START) queue_->TerryChecking(name);
    if (status.event == core::TaskStatus::SUCCESS) {
      auto exec = status.execution_info;
      if (exec->Success()) {
        auto checker_json =
            nlohmann::json::parse(checker_results->Contents(1024 * 1024));
        proto::TerryEvaluationResult result;
        result.set_score(checker_json["score"]);
        size_t num_testcase = checker_json["validation"]["cases"].size();
        const auto& validation_cases = checker_json["validation"]["cases"];
        const auto& feedback_cases = checker_json["feedback"]["cases"];
        for (size_t i = 0; i < num_testcase; i++) {
          proto::TerryTestcaseStatus testcase_status;
          if (validation_cases[i]["status"] == "missing")
            testcase_status = proto::TerryTestcaseStatus::MISSING;
          else if (feedback_cases[i]["correct"])
            testcase_status = proto::TerryTestcaseStatus::CORRECT;
          else
            testcase_status = proto::TerryTestcaseStatus::WRONG;
          result.add_testcases(testcase_status);
        }
        result.set_gen_cpu_time(generation->CpuTime());
        result.set_gen_wall_time(generation->WallTime());
        result.set_gen_memory_kb(generation->Memory());
        result.set_eval_cpu_time(execution->CpuTime());
        result.set_eval_wall_time(execution->WallTime());
        result.set_eval_memory_kb(execution->Memory());
        result.set_check_cpu_time(checker->CpuTime());
        result.set_check_wall_time(checker->WallTime());
        result.set_check_memory_kb(checker->Memory());
        result.set_seed(s_seed);
        queue_->TerryChecked(name, std::move(result), exec->Cached());
      } else {
        queue_->TerryCheckingFailure(
            name, status.message + "\n" + exec->Stderr()->Contents(1024 * 1024),
            exec->Cached());
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
  queue_->TerryGenerationWaiting(name);
}
}  // namespace manager