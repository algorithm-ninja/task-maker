#ifndef CORE_CORE_HPP
#define CORE_CORE_HPP

#include <condition_variable>
#include <future>
#include <mutex>
#include <queue>

#include "core/execution.hpp"
#include "core/file_id.hpp"
#include "core/task_status.hpp"

namespace core {

class Core {
 public:
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

  bool Run();

  Core()
      : store_directory_("files"),
        temp_directory_("temp"),
        num_cores_(std::thread::hardware_concurrency()),
        cacher_(nullptr) {}

 private:
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
