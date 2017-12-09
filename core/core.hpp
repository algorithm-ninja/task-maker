#ifndef CORE_CORE_HPP
#define CORE_CORE_HPP

#include "core/execution.hpp"
#include "core/file_id.hpp"
#include "util/flags.hpp"

namespace core {

class Core {
 public:
  struct TaskStatus {
    enum Event { START, SUCCESS, BUSY, FAILURE };
    Event event;
    std::string message;
    enum Type { FILE_LOAD, EXECUTION };
    Type type;
    const FileID* file_info;
    const Execution* execution_info;

    TaskStatus() = delete;

   private:
    friend class Core;
    static TaskStatus Start(const FileID* file) {
      // fprintf(stderr, "Start: %s\n", file->Description().c_str());
      return {START, "", FILE_LOAD, file, nullptr};
    }
    static TaskStatus Start(const Execution* execution) {
      // fprintf(stderr, "Start: %s\n", execution->Description().c_str());
      return {START, "", EXECUTION, nullptr, execution};
    }
    static TaskStatus Busy(const Execution* execution) {
      // fprintf(stderr, "Busy: %s\n", execution->Description().c_str());
      return {BUSY, "", EXECUTION, nullptr, execution};
    }
    static TaskStatus Success(const FileID* file) {
      // fprintf(stderr, "Success: %s\n", file->Description().c_str());
      return {SUCCESS, "", FILE_LOAD, file, nullptr};
    }
    static TaskStatus Success(const Execution* execution) {
      // fprintf(stderr, "Success: %s\n", execution->Description().c_str());
      return {SUCCESS, "", EXECUTION, nullptr, execution};
    }
    static TaskStatus Failure(const FileID* file, const std::string& msg) {
      // fprintf(stderr, "Failure: %s, %s\n", file->Description().c_str(),
      //        msg.c_str());
      return {FAILURE, msg, FILE_LOAD, file, nullptr};
    }
    static TaskStatus Failure(const Execution* execution,
                              const std::string& msg) {
      // fprintf(stderr, "Failure: %s, %s\n", execution->Description().c_str(),
      //        msg.c_str());
      return {FAILURE, msg, EXECUTION, nullptr, execution};
    }
  };

  FileID* LoadFile(const std::string& description, const std::string& path) {
    files_to_load_.push_back(
        std::unique_ptr<FileID>(new FileID(description, path)));
    return files_to_load_.back().get();
  }

  Execution* AddExecution(const std::string& description,
                          const std::string& executable,
                          const std::vector<std::string>& args) {
    executions_.push_back(std::unique_ptr<Execution>(
        new Execution(description, executable, args)));
    return executions_.back().get();
  }

  static void SetNumCores(int32_t num_cores) { FLAGS_num_cores = num_cores; }
  static void SetTempDirectory(const std::string& temp_directory) {
    FLAGS_temp_directory = temp_directory;
  }
  static void SetStoreDirectory(const std::string& store_directory) {
    FLAGS_store_directory = store_directory;
  }

  void SetCallback(const std::function<bool(const TaskStatus& status)>& cb) {
    callback_ = cb;
  }

  bool Run();

  Core() {
    callback_ = [](const TaskStatus& status) {
      return status.event != TaskStatus::FAILURE;
    };
  }

 private:
  std::function<bool(const TaskStatus&)> callback_;
  std::vector<std::unique_ptr<FileID>> files_to_load_;
  std::vector<std::unique_ptr<Execution>> executions_;
};

}  // namespace core

#endif
