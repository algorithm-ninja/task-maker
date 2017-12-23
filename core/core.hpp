#ifndef CORE_CORE_HPP
#define CORE_CORE_HPP

#include <condition_variable>
#include <future>
#include <mutex>
#include <queue>

#include "core/execution.hpp"
#include "core/file_id.hpp"

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

  FileID* LoadFile(const std::string& description, const std::string& path) {
    files_to_load_.push_back(std::unique_ptr<FileID>(
        new FileID(store_directory_, description, path)));
    return files_to_load_.back().get();
  }

  Execution* AddExecution(const std::string& description,
                          const std::string& executable,
                          const std::vector<std::string>& args) {
    if (!cacher_) {
      cacher_.reset(new ExecutionCacher(store_directory_));
    }
    executions_.push_back(std::unique_ptr<Execution>(
        new Execution(cacher_.get(), store_directory_, temp_directory_,
                      num_cores_, description, executable, args)));
    return executions_.back().get();
  }

  void SetNumCores(int32_t num_cores) {
    num_cores_ = num_cores;
    if (num_cores_ == 0) {
      num_cores_ = std::thread::hardware_concurrency();
    }
  }
  void SetTempDirectory(const std::string& temp_directory) {
    temp_directory_ = temp_directory;
  }
  void SetStoreDirectory(const std::string& store_directory) {
    store_directory_ = store_directory;
  }

  void SetCallback(const std::function<bool(const TaskStatus& status)>& cb) {
    callback_ = cb;
  }

  bool Run();

  Core()
      : store_directory_("files"),
        temp_directory_("temp"),
        num_cores_(std::thread::hardware_concurrency()),
        cacher_(nullptr) {
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

  std::string store_directory_;
  std::string temp_directory_;
  int num_cores_;

  std::unique_ptr<ExecutionCacher> cacher_;

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
