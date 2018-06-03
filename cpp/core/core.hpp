#ifndef CORE_CORE_HPP
#define CORE_CORE_HPP

#include <condition_variable>
#include <future>
#include <mutex>
#include <queue>

#include "core/execution.hpp"
#include "core/execution_cacher.hpp"
#include "core/file_id.hpp"
#include "core/running_task.hpp"
#include "core/task_status.hpp"
#include "glog/logging.h"

namespace core {

class Core {
 public:
  FileID* LoadFile(const std::string& description, const std::string& path) {
    std::unique_ptr<FileID> file_id = std::unique_ptr<FileID>(
        new FileID(store_directory_, description, path));
    FileID* ptr = file_id.get();
    files_to_load_.push_back(std::move(file_id));
    return ptr;
  }

  Execution* AddExecution(const std::string& description,
                          const std::string& executable,
                          const std::vector<std::string>& args,
                          bool keep_sandbox) {
    std::unique_ptr<Execution> execution = std::unique_ptr<Execution>(
        new Execution(cacher_.get(), store_directory_, temp_directory_,
                      num_cores_, description, executable, args, keep_sandbox));
    Execution* ptr = execution.get();
    executions_.push_back(std::move(execution));
    jobs_.push_back(std::unique_ptr<Job>(new Job({ptr, 0})));
    return ptr;
  }

  void SetNumCores(size_t num_cores) {
    num_cores_ = num_cores;
    if (num_cores_ == 0) num_cores_ = std::thread::hardware_concurrency();
  }
  void SetTempDirectory(const std::string& temp_directory) {
    temp_directory_ = temp_directory;
  }
  void SetStoreDirectory(const std::string& store_directory) {
    store_directory_ = store_directory;
    cacher_.reset(new ExecutionCacher(store_directory_));
  }

  bool Run();

  void Stop() { quitting_ = true; }

  std::vector<RunningTaskInfo> RunningTasks() const;

  Core()
      : store_directory_("files"),
        temp_directory_("temp"),
        num_cores_(std::thread::hardware_concurrency()),
        cacher_(nullptr) {}

 private:
  std::atomic<bool> quitting_{false};
  std::atomic<bool> failed_{false};
  std::atomic<size_t> task_id_{0};

  std::vector<std::unique_ptr<Job>> jobs_;
  std::unordered_set<Job*> waiting_jobs_;
  std::queue<ReadyTask> ready_tasks_;
  std::unordered_map<size_t, RunningTask> running_jobs_;
  std::deque<RunningTask> completed_jobs_;
  mutable std::mutex job_mutex_;
  std::condition_variable task_ready_;
  std::condition_variable task_complete_;

  std::vector<std::unique_ptr<FileID>> files_to_load_;
  std::vector<std::unique_ptr<Execution>> executions_;
  std::unordered_map<int64_t, std::vector<Job*>> dependents_;

  std::unordered_map<int64_t, util::SHA256_t> known_files_;
  std::mutex file_lock_;

  std::string store_directory_;
  std::string temp_directory_;
  size_t num_cores_;

  std::unique_ptr<ExecutionCacher> cacher_;

  util::SHA256_t GetFile(int64_t id) {
    std::lock_guard<std::mutex> lck(file_lock_);
    CHECK(known_files_.count(id) != 0u);
    return known_files_.at(id);
  }

  void SetFile(int64_t id, const util::SHA256_t& hash) {
    std::lock_guard<std::mutex> lck(file_lock_);
    known_files_[id] = hash;
  };

  void BuildDependencyGraph();

  void EnqueueJob(Job* job);
  void MarkAsSuccessful(Job* job);
  void MarkAsSuccessful(int64_t file_id);
  void MarkAsFailed(Job* job);
  void MarkAsFailed(int64_t file_id);

  bool LoadInitialFiles();
  bool ProcessTaskCompleted(RunningTask* task);

  void ThreadBody();
  TaskStatus ExecuteTask(Execution* execution);
};

}  // namespace core

#endif
