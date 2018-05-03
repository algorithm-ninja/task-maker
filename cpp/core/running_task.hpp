#ifndef CORE_WAITING_TASK_HPP
#define CORE_WAITING_TASK_HPP

#include <future>

#include "core/execution.hpp"
#include "core/file_id.hpp"

namespace core {

struct Job {
  Execution* execution;
  size_t pending_deps;
};

struct RunningTaskInfo {
  enum Type { FILE_LOAD, EXECUTION };
  Type type;

  std::string description;
  std::chrono::time_point<std::chrono::system_clock> started;

  explicit RunningTaskInfo(Execution* execution_info)
      : type(EXECUTION),
        description(execution_info->Description()),
        started(std::chrono::system_clock::now()) {}
};

struct RunningTask {
  RunningTaskInfo info;
  Job* job;
  std::future<TaskStatus> future;
};

struct ReadyTask {
  Job* job;
  std::packaged_task<TaskStatus()> task;
};

}  // namespace core

#endif
