#include "manager/generation.hpp"

namespace manager {

namespace {
void generate_input(
    const proto::TestCase& testcase, int64_t testcase_num, int64_t subtask_num,
    core::Core* core, EventQueue* queue,
    std::map<std::string, std::unique_ptr<SourceFile>>* source_cache,
    proto::CacheMode cache_mode, const std::string& executor,
    std::map<int64_t, core::FileID*>* inputs_,
    std::map<int64_t, core::FileID*>* validation_) {
  if (!testcase.input_file().empty()) {
    (*inputs_)[testcase_num] = core->LoadFile(
        "Static input " + std::to_string(testcase_num), testcase.input_file());
    queue->Validated(testcase_num);
  } else if (testcase.has_generator() && testcase.has_validator()) {
    const std::string& generator = testcase.generator().path();
    const std::string& validator = testcase.validator().path();

    std::vector<std::string> args(testcase.args().begin(),
                                  testcase.args().end());
    core::Execution* gen = (*source_cache)[generator]->execute(
        "Generation of input " + std::to_string(testcase_num), args);
    gen->SetCallback(
        [queue, testcase_num](const core::TaskStatus& status) -> bool {
          if (status.event == core::TaskStatus::FAILURE) {
            queue->GenerationFailure(testcase_num, status.message);
            return false;
          }
          if (status.type == core::TaskStatus::FILE_LOAD) return true;
          if (status.event == core::TaskStatus::START)
            queue->Generating(testcase_num);
          if (status.event == core::TaskStatus::SUCCESS) {
            auto exec = status.execution_info;
            if (exec->Success()) {
              queue->Generated(testcase_num);
            } else {
              queue->GenerationFailure(
                  testcase_num,
                  status.message + "\n" +
                      status.execution_info->Stderr()->Contents(1024 * 1024));
              return false;
            }
          }
          return true;
        });
    for (const proto::Dependency& dep : testcase.extra_deps()) {
      core::FileID* file_id =
          core->LoadFile("Testcase " + std::to_string(testcase_num) +
                             " dependency " + dep.name(),
                         dep.path());
      gen->Input(dep.name(), file_id);
    }
    if (!executor.empty()) gen->SetExecutor(executor);
    if (cache_mode == proto::GENERATION || cache_mode == proto::ALL)
      gen->SetCachingMode(core::Execution::CachingMode::ALWAYS);
    else
      gen->SetCachingMode(core::Execution::CachingMode::NEVER);
    (*inputs_)[testcase_num] = gen->Stdout();
    queue->GenerationWaiting(testcase_num);

    core::Execution* val = (*source_cache)[validator]->execute(
        "Validation of input " + std::to_string(testcase_num),
        {"input", std::to_string(subtask_num + 1)});
    val->SetCallback(
        [queue, testcase_num](const core::TaskStatus& status) -> bool {
          if (status.event == core::TaskStatus::FAILURE) {
            queue->GenerationFailure(testcase_num, status.message);
            return false;
          }
          if (status.type == core::TaskStatus::FILE_LOAD) return true;
          if (status.event == core::TaskStatus::START)
            queue->Validating(testcase_num);
          if (status.event == core::TaskStatus::SUCCESS) {
            auto exec = status.execution_info;
            if (exec->Success()) {
              queue->Validated(testcase_num);
            } else {
              queue->GenerationFailure(
                  testcase_num,
                  status.message + "\n" +
                      status.execution_info->Stderr()->Contents(1024 * 1024));
              return false;
            }
          }
          return true;
        });
    if (!executor.empty()) val->SetExecutor(executor);
    if (cache_mode == proto::GENERATION || cache_mode == proto::ALL)
      val->SetCachingMode(core::Execution::CachingMode::ALWAYS);
    else
      val->SetCachingMode(core::Execution::CachingMode::NEVER);
    val->Input("input", (*inputs_)[testcase_num]);
    (*validation_)[testcase_num] = val->Stdout();
  } else {
    throw std::logic_error(
        "Generator and validator or static input not"
        "provided for input " +
        std::to_string(testcase_num));
  }
}

void generate_output(const proto::TestCase& testcase, int64_t testcase_num,
                     core::Core* core, EventQueue* queue,
                     const std::unique_ptr<SourceFile>& solution_,
                     proto::CacheMode cache_mode, const std::string& executor,
                     const proto::Task& task,
                     std::map<int64_t, core::FileID*>* inputs_,
                     std::map<int64_t, core::FileID*>* outputs_,
                     std::map<int64_t, core::FileID*>* validation_) {
  if (!testcase.output_file().empty()) {
    (*outputs_)[testcase_num] =
        core->LoadFile("Static output " + std::to_string(testcase_num),
                       testcase.output_file());
    queue->GenerationDone(testcase_num);
  } else if (solution_) {
    core::Execution* sol = solution_->execute(
        "Generation of output " + std::to_string(testcase_num), {});
    sol->SetCallback(
        [queue, testcase_num](const core::TaskStatus& status) -> bool {
          if (status.event == core::TaskStatus::FAILURE) {
            queue->GenerationFailure(testcase_num, status.message);
            return false;
          }
          if (status.type == core::TaskStatus::FILE_LOAD) return true;
          if (status.event == core::TaskStatus::START)
            queue->Solving(testcase_num);
          if (status.event == core::TaskStatus::SUCCESS) {
            auto exec = status.execution_info;
            if (exec->Success()) {
              queue->GenerationDone(testcase_num);
            } else {
              queue->GenerationFailure(
                  testcase_num,
                  status.message + "\n" +
                      status.execution_info->Stderr()->Contents(1024 * 1024));
              return false;
            }
          }

          return true;
        });
    if (!executor.empty()) sol->SetExecutor(executor);
    if (cache_mode == proto::GENERATION || cache_mode == proto::ALL)
      sol->SetCachingMode(core::Execution::CachingMode::ALWAYS);
    else
      sol->SetCachingMode(core::Execution::CachingMode::NEVER);

    if (validation_->count(testcase_num) != 0)
      sol->Input("wait_for_validation", (*validation_)[testcase_num]);

    if (task.input_file().empty())
      sol->Stdin((*inputs_)[testcase_num]);
    else
      sol->Input(task.input_file(), (*inputs_)[testcase_num]);

    if (task.output_file().empty())
      (*outputs_)[testcase_num] = sol->Stdout();
    else
      (*outputs_)[testcase_num] = sol->Output(task.output_file());
  } else {
    throw std::logic_error("No solution provided for generating output " +
                           std::to_string(testcase_num));
  }
}
}  // namespace

Generation::Generation(EventQueue* queue, core::Core* core,
                       const proto::Task& task, proto::CacheMode cache_mode,
                       const std::string& executor) {
  // TODO(edomora97) set executor and cache_mode in the compilations
  task_ = task;
  if (task.has_official_solution()) {
    absl::optional<proto::GraderInfo> info;
    for (auto grader : task.grader_info())
      if (task.official_solution().language() == grader.for_language()) {
        info = grader;
        break;
      }
    solution_ = SourceFile::FromProto(queue, core, task.official_solution(),
                                      info, true);
  }
  if (task.has_checker())
    checker_ = SourceFile::FromProto(queue, core, task.checker(), {}, true);

  for (auto subtask : task.subtasks()) {
    for (auto testcase_kv : subtask.second.testcases()) {
      auto testcase = testcase_kv.second;
      // compile generator/validator
      if (testcase.has_generator())
        if (source_cache_.count(testcase.generator().path()) == 0)
          source_cache_[testcase.generator().path()] = SourceFile::FromProto(
              queue, core, testcase.generator(), {}, true);
      if (testcase.has_validator())
        if (source_cache_.count(testcase.validator().path()) == 0)
          source_cache_[testcase.validator().path()] = SourceFile::FromProto(
              queue, core, testcase.validator(), {}, true);

      generate_input(testcase, testcase_kv.first, subtask.first, core, queue,
                     &source_cache_, cache_mode, executor, &inputs_,
                     &validation_);

      generate_output(testcase, testcase_kv.first, core, queue, solution_,
                      cache_mode, executor, task, &inputs_, &outputs_,
                      &validation_);
    }
  }
}

// To be called after Core.Run
void Generation::WriteInputs(const proto::EvaluateTaskRequest& request) {
  auto map = request.write_inputs_to();
  for (auto input : inputs_) {
    if (map.count(input.first) == 0) {
      throw std::range_error("Missing destination for input " +
                             std::to_string(input.first));
    } else {
      input.second->WriteTo(map[input.first]);
    }
  }
}
void Generation::WriteOutputs(const proto::EvaluateTaskRequest& request) {
  auto map = request.write_outputs_to();
  for (auto output : outputs_) {
    if (map.count(output.first) == 0) {
      throw std::range_error("Missing destination for output " +
                             std::to_string(output.first));
    } else {
      output.second->WriteTo(map[output.first]);
    }
  }
}
void Generation::WriteChecker(const proto::EvaluateTaskRequest& request) {
  if (!checker_) throw std::logic_error("There is not checker to write");
  if (request.write_checker_to().empty())
    throw std::range_error("write_checker_to not provided");
  checker_->WriteTo(request.write_checker_to(), true, true);
}
}  // namespace manager
