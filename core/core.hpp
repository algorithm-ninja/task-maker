#ifndef CORE_CORE_HPP
#define CORE_CORE_HPP

#include <condition_variable>
#include <future>
#include <mutex>
#include <queue>

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
    FileID* file_info;
    Execution* execution_info;

    TaskStatus() = delete;

   private:
    friend class Core;
    static TaskStatus Start(FileID* file) {
      // fprintf(stderr, "Start: %s\n", file->Description().c_str());
      return {START, "", FILE_LOAD, file, nullptr};
    }
    static TaskStatus Start(Execution* execution) {
      // fprintf(stderr, "Start: %s\n", execution->Description().c_str());
      return {START, "", EXECUTION, nullptr, execution};
    }
    static TaskStatus Busy(Execution* execution) {
      // fprintf(stderr, "Busy: %s\n", execution->Description().c_str());
      return {BUSY, "", EXECUTION, nullptr, execution};
    }
    static TaskStatus Success(FileID* file) {
      // fprintf(stderr, "Success: %s\n", file->Description().c_str());
      return {SUCCESS, "", FILE_LOAD, file, nullptr};
    }
    static TaskStatus Success(Execution* execution) {
      // fprintf(stderr, "Success: %s\n", execution->Description().c_str());
      return {SUCCESS, "", EXECUTION, nullptr, execution};
    }
    static TaskStatus Failure(FileID* file, const std::string& msg) {
      // fprintf(stderr, "Failure: %s, %s\n", file->Description().c_str(),
      //        msg.c_str());
      return {FAILURE, msg, FILE_LOAD, file, nullptr};
    }
    static TaskStatus Failure(Execution* execution, const std::string& msg) {
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

  std::queue<std::packaged_task<TaskStatus()>> tasks_;
  std::mutex task_mutex_;
  std::condition_variable task_ready_;
  std::atomic<bool> quitting_{false};

  std::unordered_map<int64_t, util::SHA256_t> known_files_;
  std::mutex file_lock_;

  util::SHA256_t GetFile(int64_t id) {
    std::lock_guard<std::mutex> lck(file_lock_);
    if (known_files_.count(id) == 0u) {
      throw std::logic_error("Unknown file requested");
    }
    return known_files_.at(id);
  }

  void SetFile(int64_t id, const util::SHA256_t& hash) {
    std::lock_guard<std::mutex> lck(file_lock_);
    known_files_[id] = hash;
  };

  bool FilePresent(int64_t id) {
    std::lock_guard<std::mutex> lck(file_lock_);
    return known_files_.count(id) != 0u;
  }

  TaskStatus LoadFileTask(FileID* file);

  TaskStatus ExecuteTask(Execution* execution);

  void ThreadBody();
};

}  // namespace core

#endif
