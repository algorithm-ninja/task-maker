#ifndef MANAGER_EVALUATION_HPP
#define MANAGER_EVALUATION_HPP

#include "core/core.hpp"
#include "manager/event_queue.hpp"
#include "manager/generation.hpp"
#include "manager/source_file.hpp"
#include "proto/manager.pb.h"
#include "proto/task.pb.h"

namespace manager {

class Evaluation {
 public:
  Evaluation(EventQueue* queue, core::Core* core, const Generation& generation,
             const proto::Task& task, bool exclusive,
             proto::CacheMode cache_mode, std::string executor,
             bool keep_sandbox);

  void Evaluate(SourceFile* solution);

 private:
  struct EvaluationStatus {
    std::map<int64_t, float> subtask_scores;
    std::map<int64_t, float> testcase_scores;
    float task_score;
  };

  EventQueue* queue_;
  core::Core* core_;
  const Generation& generation_;
  proto::Task task_;
  bool exclusive_;
  proto::CacheMode cache_mode_;
  std::string executor_;
  bool keep_sandbox_;
  std::map<std::string, EvaluationStatus> status_;
  std::map<int64_t, std::vector<int64_t>> testcases_of_subtask;

  void evaluate_testcase_(int64_t subtask_num, int64_t testcase_num,
                          SourceFile* solution);
  void UpdateScore(const std::string &name, int64_t subtask_num,
                   int64_t testcase_num, float score);
};

}  // namespace manager

#endif
