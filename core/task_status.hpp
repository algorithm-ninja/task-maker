#ifndef CORE_TASK_STATUS_HPP
#define CORE_TASK_STATUS_HPP

#include <string>

namespace core {

class FileID;
class Execution;

struct TaskStatus {
  enum Event { START, SUCCESS, BUSY, FAILURE };
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
    // fprintf(stderr, "Start: %s\n", file->Description().c_str());
    return TaskStatus(START, "", FILE_LOAD, file, nullptr);
  }
  static TaskStatus Start(Execution* execution) {
    // fprintf(stderr, "Start: %s\n", execution->Description().c_str());
    return TaskStatus(START, "", EXECUTION, nullptr, execution);
  }
  static TaskStatus Busy(Execution* execution) {
    // fprintf(stderr, "Busy: %s\n", execution->Description().c_str());
    return TaskStatus(BUSY, "", EXECUTION, nullptr, execution);
  }
  static TaskStatus Success(FileID* file) {
    // fprintf(stderr, "Success: %s\n", file->Description().c_str());
    return TaskStatus(SUCCESS, "", FILE_LOAD, file, nullptr);
  }
  static TaskStatus Success(Execution* execution) {
    // fprintf(stderr, "Success: %s\n", execution->Description().c_str());
    return TaskStatus(SUCCESS, "", EXECUTION, nullptr, execution);
  }
  static TaskStatus Failure(FileID* file, const std::string& msg) {
    // fprintf(stderr, "Failure: %s, %s\n", file->Description().c_str(),
    //        msg.c_str());
    return TaskStatus(FAILURE, msg, FILE_LOAD, file, nullptr);
  }
  static TaskStatus Failure(Execution* execution, const std::string& msg) {
    // fprintf(stderr, "Failure: %s, %s\n", execution->Description().c_str(),
    //        msg.c_str());
    return TaskStatus(FAILURE, msg, EXECUTION, nullptr, execution);
  }
};

}  // namespace core

#endif
