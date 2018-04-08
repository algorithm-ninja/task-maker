#ifndef CORE_TASK_STATUS_HPP
#define CORE_TASK_STATUS_HPP

#include <string>

namespace core {

class FileID;
class Execution;

struct TaskStatus {
  enum Event {
    START,    // before the action starts
    SUCCESS,  // after the action completes successfully
    BUSY,     // the execution is resheduled because of a lack of executors
    FAILURE,  // the action failed (because of an internal error, e.g the
              // sandbox failed)
    FINISH_SUCCESS,  // the core exited successfully
    FINISH_FAILED    // the core exited with an error
  };
  Event event;
  std::string message;
  enum Type { FILE_LOAD, EXECUTION };
  Type type;
  FileID* file_info;
  Execution* execution_info;

  TaskStatus() = delete;
  TaskStatus(Event event, std::string message, Type type, FileID* file_info,
             Execution* execution_info)
      : event(event),
        message(std::move(message)),
        type(type),
        file_info(file_info),
        execution_info(execution_info) {}

 private:
  friend class Core;
  static TaskStatus Start(FileID* file) {
    return TaskStatus(START, "", FILE_LOAD, file, nullptr);
  }
  static TaskStatus Start(Execution* execution) {
    return TaskStatus(START, "", EXECUTION, nullptr, execution);
  }
  static TaskStatus Busy(Execution* execution) {
    return TaskStatus(BUSY, "", EXECUTION, nullptr, execution);
  }
  static TaskStatus Success(FileID* file) {
    return TaskStatus(SUCCESS, "", FILE_LOAD, file, nullptr);
  }
  static TaskStatus Success(Execution* execution) {
    return TaskStatus(SUCCESS, "", EXECUTION, nullptr, execution);
  }
  static TaskStatus Failure(FileID* file, const std::string& msg) {
    return TaskStatus(FAILURE, msg, FILE_LOAD, file, nullptr);
  }
  static TaskStatus Failure(Execution* execution, const std::string& msg) {
    return TaskStatus(FAILURE, msg, EXECUTION, nullptr, execution);
  }
  static TaskStatus Finish(FileID* file, bool success) {
    return TaskStatus(success ? FINISH_SUCCESS : FINISH_FAILED, "", FILE_LOAD,
                      file, nullptr);
  }
  static TaskStatus Finish(Execution* execution, bool success) {
    return TaskStatus(success ? FINISH_SUCCESS : FINISH_FAILED, "", EXECUTION,
                      nullptr, execution);
  }
};

}  // namespace core

#endif
