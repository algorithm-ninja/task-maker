#ifndef CORE_WAITING_TASK_HPP
#define CORE_WAITING_TASK_HPP

#include "core/execution.hpp"
#include "core/file_id.hpp"
#include <future>

namespace core {

struct WaitingTask {
  enum Type { FILE_LOAD, EXECUTION };
  Type type;

  Execution* execution_info;
  FileID* file_info;

  std::future<TaskStatus> future;

  WaitingTask(Execution* execution_info, std::future<TaskStatus> future)
      : type(EXECUTION),
        execution_info(execution_info),
        file_info(nullptr),
        future(std::move(future)) {}
  WaitingTask(FileID* file_info, std::future<TaskStatus> future)
      : type(FILE_LOAD),
        execution_info(nullptr),
        file_info(file_info),
        future(std::move(future)) {}
};

}  // namespace core

#endif
