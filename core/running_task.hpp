#ifndef CORE_WAITING_TASK_HPP
#define CORE_WAITING_TASK_HPP

#include <future>

#include "core/execution.hpp"
#include "core/file_id.hpp"

namespace core {

struct RunningTaskInfo {
  enum Type { FILE_LOAD, EXECUTION };
  Type type;

  std::string description;
  std::chrono::time_point<std::chrono::system_clock> started;

  explicit RunningTaskInfo(Execution* execution_info)
      : type(EXECUTION),
        description(execution_info->Description()),
        started(std::chrono::system_clock::now()) {}
  explicit RunningTaskInfo(FileID* file_info)
      : type(FILE_LOAD),
        description(file_info->Description()),
        started(std::chrono::system_clock::now()) {}
};

struct RunningTask {
  RunningTaskInfo info;
  std::future<TaskStatus> future;

  RunningTask(Execution* execution_info, std::future<TaskStatus> future)
      : info(execution_info), future(std::move(future)) {}
  RunningTask(FileID* file_info, std::future<TaskStatus> future)
      : info(file_info), future(std::move(future)) {}
};

}  // namespace core

#endif
