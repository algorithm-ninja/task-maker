#include "manager/evaluation.hpp"
#include "glog/logging.h"

namespace manager {

Evaluation::Evaluation(EventQueue* queue, core::Core* core,
                       const Generation& generation, const proto::Task& task,
                       bool exclusive, proto::CacheMode cache_mode,
                       const std::string& executor)
    : generation_(generation) {
  queue_ = queue;
  core_ = core;
  task_ = task;
  exclusive_ = exclusive;
  cache_mode_ = cache_mode;

  for (auto subtask : task.subtasks()) {
    for (auto testcase : subtask.second.testcases()) {
      testcases_of_subtask[subtask.first].push_back(testcase.first);
    }
  }
}

void Evaluation::Evaluate(SourceFile* solution) {
  LOG(INFO) << "Evaluating " << solution->Name();
  std::string name = solution->Name();
  status_[name].task_score = -1;  // assuming you cannot make negative points

  for (auto subtask : task_.subtasks()) {
    for (auto testcase : subtask.second.testcases()) {
      evaluate_testcase_(subtask.first, testcase.first, solution);
    }
  }
}

void Evaluation::evaluate_testcase_(int64_t subtask_num, int64_t testcase_num,
                                    SourceFile* solution) {
  std::string name = solution->Name();
  std::string s_testcase_num = std::to_string(testcase_num);

  core::Execution* execution = solution->execute(
      "Evaluation of " + name + " on testcase " + s_testcase_num, {});
  execution->CpuLimit(task_.time_limit());
  execution->WallLimit(task_.time_limit() * 1.5f);
  execution->MemoryLimit(task_.memory_limit_kb());
  if (exclusive_) execution->SetExclusive();
  if (cache_mode_ == proto::ALL)
    execution->SetCachingMode(core::Execution::SAME_EXECUTOR);
  else
    execution->SetCachingMode(core::Execution::NEVER);
  if (!executor_.empty()) execution->SetExecutor(executor_);
  // setup solution i/o
  if (task_.input_file().empty())
    execution->Stdin(generation_.GetInput(testcase_num));
  else
    execution->Input(task_.input_file(), generation_.GetInput(testcase_num));
  core::FileID* output;
  if (task_.output_file().empty())
    output = execution->Stdout();
  else
    output = execution->Output(task_.output_file());
  execution->SetCallback([this, name, testcase_num,
                          subtask_num](const core::TaskStatus& status) -> bool {
    if (status.type == core::TaskStatus::FILE_LOAD)
      return !(status.event == core::TaskStatus::FAILURE);
    if (status.event == core::TaskStatus::START)
      queue_->Executing(name, testcase_num);
    if (status.event == core::TaskStatus::SUCCESS) {
      auto exec = status.execution_info;
      if (exec->Success()) {
        queue_->Executed(name, testcase_num);
      } else {
        queue_->EvaluationDone(name, testcase_num, 0.0, exec->Message(),
                               exec->CpuTime(), exec->WallTime(),
                               exec->Memory());
        UpdateScore(name, subtask_num, testcase_num, 0.0);
      }
    }
    if (status.event == core::TaskStatus::FAILURE) {
      queue_->FatalError(status.message + ": " +
                         status.execution_info->Message());
      return false;
    }
    return true;
  });

  core::Execution* checker;
  if (task_.has_checker()) {
    checker = generation_.GetChecker()->execute(
        "Checking solution " + name + " for testcase " + s_testcase_num,
        {"input", "output", "contestant_output"});
    checker->Input("input", generation_.GetInput(testcase_num));
  } else {
    // TODO(veluca): replace this with our own utility?
    checker = core_->AddExecution(
        "Checking solution " + name + " for testcase " + s_testcase_num,
        // TODO(edomora97) getting the real path of diff is hard (which command)
        "/usr/bin/diff", {"-w", "output", "contestant_output"});
  }
  checker->Input("output", generation_.GetOutput(testcase_num));
  checker->Input("contestant_output", output);
  checker->CpuLimit(10 * task_.time_limit());
  checker->MemoryLimit(10 * task_.memory_limit_kb());
  if (cache_mode_ == proto::ALL)
    checker->SetCachingMode(core::Execution::ALWAYS);
  else
    checker->SetCachingMode(core::Execution::NEVER);
  if (!executor_.empty()) checker->SetExecutor(executor_);
  checker->SetCallback([this, name, subtask_num, testcase_num, checker,
                        execution](const core::TaskStatus& status) -> bool {
    if (status.type == core::TaskStatus::FILE_LOAD)
      return !(status.event == core::TaskStatus::FAILURE);
    if (status.event == core::TaskStatus::START) {
      queue_->Checking(name, testcase_num);
      return true;
    }

    if (!task_.has_checker()) {
      // without the checker diff is used to check and it exits with (1) if the
      // files differ.
      if (status.execution_info->Success()) {
        queue_->EvaluationDone(name, testcase_num, 1.0f, "Output is correct",
                               execution->CpuTime(), execution->WallTime(),
                               execution->Memory());
        UpdateScore(name, subtask_num, testcase_num, 1.0);
      } else {
        queue_->EvaluationDone(name, testcase_num, 0.0f,
                               "Output is not correct", execution->CpuTime(),
                               execution->WallTime(), execution->Memory());
        UpdateScore(name, subtask_num, testcase_num, 0.0);
      }
    } else {
      if (status.execution_info->Success()) {
        std::string out = checker->Stdout()->Contents(1024 * 1024);
        std::string err = checker->Stderr()->Contents(1024 * 1024);
        try {
          float score = std::stof(out);
          if (score < 0.0 || score > 1.0)
            throw std::invalid_argument("score not in range [0.0, 1.0]");
          queue_->EvaluationDone(name, testcase_num, score, err,
                                 execution->CpuTime(), execution->WallTime(),
                                 execution->Memory());
          UpdateScore(name, subtask_num, testcase_num, score);
        } catch (const std::invalid_argument& ex) {
          queue_->EvaluationFailure(name, testcase_num, "checker failed",
                                    execution->CpuTime(), execution->WallTime(),
                                    execution->Memory());
          queue_->FatalError(std::string("Checker returned invalid score: ") +
                             ex.what() + "\n" + "The stdout was: " + out +
                             "\n" + "The stderr was: " + err);
          return false;
        }
      } else {
        std::string checker_error = checker->Stderr()->Contents(1024 * 1024);
        queue_->EvaluationFailure(
            name, testcase_num, checker->Message() + "\n" + checker_error,
            execution->CpuTime(), execution->WallTime(), execution->Memory());
        queue_->FatalError("Checker failed: " + checker_error);
        return false;
      }
    }
    return true;
  });

  queue_->EvaluationWaiting(name, testcase_num);
}
void Evaluation::UpdateScore(const std::string& name, int64_t subtask_num,
                             int64_t testcase_num, float score) {
  Evaluation::EvaluationStatus& status = status_[name];
  proto::ScoreMode score_mode = task_.subtasks().at(subtask_num).score_mode();
  status.testcase_scores[testcase_num] = score;
  for (int64_t testcase : testcases_of_subtask[subtask_num])
    if (status.testcase_scores.count(testcase) == 0) return;
  float st_score = 0;
  std::function<float(float, float)> acc = nullptr;
  switch (score_mode) {
    case proto::MIN:
      st_score = 1.0;
      acc = [](float score1, float score2) { return std::min(score1, score2); };
      break;
    case proto::MAX:
      st_score = 0.0;
      acc = [](float score1, float score2) { return std::max(score1, score2); };
      break;
    case proto::SUM:
      st_score = 0.0;
      acc = [](float score1, float score2) { return score1 + score2; };
      break;
    default:
      throw std::domain_error("Invalid score mode for subtask " +
                              std::to_string(subtask_num));
  }
  for (int64_t testcase : testcases_of_subtask[subtask_num])
    if (status.testcase_scores.count(testcase) > 0)
      st_score = acc(st_score, status.testcase_scores[testcase]);
  st_score *= task_.subtasks().at(subtask_num).max_score();
  if (score_mode == proto::SUM)
    st_score /= testcases_of_subtask[subtask_num].size();

  if (status.subtask_scores.count(subtask_num) == 0 ||
      st_score != status.subtask_scores.at(subtask_num))
    queue_->SubtaskTaskScore(name, st_score, subtask_num);
  status.subtask_scores[subtask_num] = st_score;

  float task_score = 0;
  for (auto subtask : status.subtask_scores) task_score += subtask.second;
  if (task_score != status.task_score) queue_->TaskScore(name, task_score);
  status.task_score = task_score;
}
}  // namespace manager
