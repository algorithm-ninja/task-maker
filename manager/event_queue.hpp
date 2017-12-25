#ifndef MANAGER_EVENT_QUEUE_HPP
#define MANAGER_EVENT_QUEUE_HPP

#include <queue>

#include "absl/base/thread_annotations.h"
#include "absl/synchronization/mutex.h"
#include "absl/types/optional.h"
#include "proto/event.pb.h"

namespace manager {

class EventQueue {
 public:
  void FatalError(const std::string& message) {
    proto::Event event;
    event.mutable_fatal_error()->set_msg(message);
    Enqueue(std::move(event));
  }
  void TaskScore(const std::string& solution, float score) {
    proto::Event event;
    auto* sub_event = event.mutable_task_score();
    sub_event->set_solution(solution);
    sub_event->set_score(score);
    Enqueue(std::move(event));
  }
  void SubtaskTaskScore(const std::string& solution, float score,
                        int64_t subtask_id) {
    proto::Event event;
    auto* sub_event = event.mutable_subtask_score();
    sub_event->set_solution(solution);
    sub_event->set_score(score);
    sub_event->set_subtask_id(subtask_id);
    Enqueue(std::move(event));
  }
  void CompilationWaiting(const std::string& filename) {
    Compilation(filename, proto::Status::WAITING);
  }
  void CompilationRunning(const std::string& filename) {
    Compilation(filename, proto::Status::RUNNING);
  }
  void CompilationSuccess(const std::string& filename,
                          const std::string& errors) {
    Compilation(filename, proto::Status::SUCCESS, errors);
  }
  void CompilationFailure(const std::string& filename,
                          const std::string& errors) {
    Compilation(filename, proto::Status::FAILURE, errors);
  }
  void GenerationWaiting(int64_t testcase) {
    Generation(testcase, proto::Status::WAITING);
  }
  void Generating(int64_t testcase) {
    Generation(testcase, proto::Status::GENERATING);
  }
  void Generated(int64_t testcase) {
    Generation(testcase, proto::Status::GENERATED);
  }
  void Validating(int64_t testcase) {
    Generation(testcase, proto::Status::VALIDATING);
  }
  void Validated(int64_t testcase) {
    Generation(testcase, proto::Status::VALIDATED);
  }
  void Solving(int64_t testcase) {
    Generation(testcase, proto::Status::SOLVING);
  }
  void GenerationSuccess(int64_t testcase) {
    Generation(testcase, proto::Status::SUCCESS);
  }
  void GenerationFailure(int64_t testcase, const std::string& errors) {
    Generation(testcase, proto::Status::FAILURE, errors);
  }
  void EvaluationWaiting(const std::string& solution, int64_t testcase) {
    Evaluation(solution, testcase, proto::Status::WAITING);
  }
  void Executing(const std::string& solution, int64_t testcase) {
    Evaluation(solution, testcase, proto::Status::EXECUTING);
  }
  void Executed(const std::string& solution, int64_t testcase) {
    Evaluation(solution, testcase, proto::Status::EXECUTED);
  }
  void Checking(const std::string& solution, int64_t testcase) {
    Evaluation(solution, testcase, proto::Status::CHECKING);
  }
  void EvaluationSuccess(const std::string& solution, int64_t testcase,
                         float score, const std::string& message,
                         float cpu_time, float wall_time, int64_t memory) {
    proto::EvaluationResult result;
    result.set_score(score);
    result.set_message(message);
    result.set_cpu_time_used(cpu_time);
    result.set_wall_time_used(wall_time);
    result.set_memory_used_kb(memory);
    Evaluation(solution, testcase, proto::Status::SUCCESS, std::move(result));
  }
  void EvaluationFailure(const std::string& solution, int64_t testcase,
                         const std::string& message, float cpu_time,
                         float wall_time, int64_t memory) {
    proto::EvaluationResult result;
    result.set_message(message);
    result.set_cpu_time_used(cpu_time);
    result.set_wall_time_used(wall_time);
    result.set_memory_used_kb(memory);
    Evaluation(solution, testcase, proto::Status::FAILURE, std::move(result));
  }
  absl::optional<proto::Event> Dequeue();
  void Stop();

 private:
  absl::Mutex queue_mutex_;
  std::queue<proto::Event> queue_ GUARDED_BY(queue_mutex_);
  bool stopped_ GUARDED_BY(queue_mutex_) = false;
  void Enqueue(proto::Event&& event);
  void Compilation(const std::string& filename, proto::Status status,
                   const std::string& errors = "") {
    proto::Event event;
    auto* sub_event = event.mutable_compilation();
    sub_event->set_filename(filename);
    sub_event->set_status(status);
    if (!errors.empty()) {
      sub_event->set_stderr(errors);
    }
    Enqueue(std::move(event));
  }
  void Generation(int64_t testcase, proto::Status status,
                  const std::string& errors = "") {
    proto::Event event;
    auto* sub_event = event.mutable_generation();
    sub_event->set_testcase(testcase);
    sub_event->set_status(status);
    if (!errors.empty()) {
      sub_event->set_error(errors);
    }
    Enqueue(std::move(event));
  }
  void Evaluation(const std::string& solution, int64_t testcase,
                  proto::Status status,
                  absl::optional<proto::EvaluationResult>&& result = {}) {
    proto::Event event;
    auto* sub_event = event.mutable_evaluation();
    sub_event->set_solution(solution);
    sub_event->set_testcase(testcase);
    sub_event->set_status(status);
    if (result.has_value()) {
      sub_event->mutable_result()->Swap(&result.value());
    }
    Enqueue(std::move(event));
  }
};

}  // namespace manager

#endif
