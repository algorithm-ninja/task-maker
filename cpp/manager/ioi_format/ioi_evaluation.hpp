#ifndef MANAGER_IOI_EVALUATION_HPP
#define MANAGER_IOI_EVALUATION_HPP

#include "core/core.hpp"
#include "manager/evaluation.hpp"
#include "manager/event_queue.hpp"
#include "manager/ioi_format/ioi_generation.hpp"
#include "manager/source_file.hpp"
#include "proto/manager.pb.h"
#include "proto/task.pb.h"

namespace manager {

class IOIEvaluation : public Evaluation {
 public:
  IOIEvaluation() = default;

  IOIEvaluation(EventQueue* queue, core::Core* core, IOIGeneration* generation,
                const proto::Task& task, bool exclusive, float extra_time,
                proto::CacheMode cache_mode, std::string executor,
                bool keep_sandbox);

  void Evaluate(SourceFile* solution);

 private:
  struct EvaluationStatus {
    std::map<int64_t, float> subtask_scores;
    std::map<int64_t, float> testcase_scores;
    float task_score;
  };

  EventQueue* queue_ = nullptr;
  core::Core* core_ = nullptr;
  IOIGeneration* generation_ = nullptr;
  proto::Task task_;
  bool exclusive_ = false;
  float extra_time_ = 0;
  proto::CacheMode cache_mode_ = proto::CacheMode::ALL;
  std::string executor_;
  bool keep_sandbox_ = false;
  std::map<std::string, EvaluationStatus> status_;
  std::map<int64_t, std::vector<int64_t>> testcases_of_subtask;

  void evaluate_testcase_(int64_t subtask_num, int64_t testcase_num,
                          SourceFile* solution);
  void UpdateScore(const std::string& name, int64_t subtask_num,
                   int64_t testcase_num, float score);
};

}  // namespace manager

#endif  // MANAGER_IOI_EVALUATION_HPP
