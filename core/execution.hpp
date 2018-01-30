#ifndef CORE_EXECUTION_HPP
#define CORE_EXECUTION_HPP

#include <functional>
#include <unordered_map>
#include <vector>

#include "core/execution_cacher.hpp"
#include "core/file_id.hpp"
#include "core/task_status.hpp"
#include "executor/executor.hpp"
#include "proto/response.pb.h"

namespace core {

class Execution {
 public:
  enum CachingMode { NEVER, SAME_EXECUTOR, ALWAYS };

  const std::string& Description() const { return description_; }
  int64_t ID() const { return id_; }

  void Stdin(const FileID* in) { stdin_ = in->ID(); }
  void Input(const std::string& name, const FileID* id) {
    inputs_.emplace(name, id->ID());
  }

  FileID* Stdout() { return stdout_.get(); }
  FileID* Stderr() { return stderr_.get(); }
  FileID* Output(const std::string& name) {
    return Output(name, name + " for " + Description());
  }

  FileID* Output(const std::string& name, const std::string& description);

  void CpuLimit(float limit) { resource_limits_.set_cpu_time(limit); }
  void WallLimit(float limit) { resource_limits_.set_wall_time(limit); }
  void MemoryLimit(int64_t kb) { resource_limits_.set_memory(kb); }
  void ProcessLimit(int32_t limit) { resource_limits_.set_processes(limit); }
  void FileLimit(int32_t limit) { resource_limits_.set_nfiles(limit); }
  void FileSizeLimit(int64_t kb) { resource_limits_.set_fsize(kb); }
  void MemoryLockLimit(int64_t limit) { resource_limits_.set_mlock(limit); }
  void StackLimit(int64_t limit) { resource_limits_.set_stack(limit); }

  void SetExclusive() { exclusive_ = true; }
  void SetCachingMode(CachingMode mode) { caching_mode_ = mode; }
  void SetExecutor(const std::string& executor) { executor_ = executor; }

  void SetCallback(const std::function<bool(const TaskStatus& status)>& cb) {
    callback_ = cb;
  }

  // To be called after Core::Run().
  bool Success() const { return successful_; }
  std::string Message() const { return message_; }
  float CpuTime() const { return response_.resource_usage().cpu_time(); }
  float SysTime() const { return response_.resource_usage().sys_time(); }
  float WallTime() const { return response_.resource_usage().wall_time(); }
  int64_t Memory() const { return response_.resource_usage().memory(); }

  int32_t StatusCode() const { return response_.status_code(); }
  int32_t Signal() const { return response_.signal(); }

  Execution(const Execution&) = delete;
  Execution& operator=(const Execution&) = delete;
  Execution(Execution&&) = delete;
  Execution& operator=(Execution&&) = delete;
  ~Execution() = default;

 private:
  friend class Core;
  std::vector<int64_t> Deps() const;
  proto::Response RunWithCache(executor::Executor* executor,
                               const proto::Request& request);
  void Run(const std::function<util::SHA256_t(int64_t)>& get_hash,
           const std::function<void(int64_t, const util::SHA256_t&)>& set_hash);

  bool IsExclusive() const { return exclusive_; }

  Execution(ExecutionCacher* cacher, std::string store_directory,
            std::string temp_directory, int num_cores, std::string description,
            std::string executable, std::vector<std::string> args,
            bool keep_sandbox)
      : store_directory_(std::move(store_directory)),
        temp_directory_(std::move(temp_directory)),
        num_cores_(num_cores),
        description_(std::move(description)),
        id_((reinterpret_cast<int64_t>(&next_id_) << 32) | (next_id_++)),
        executable_(std::move(executable)),
        args_(std::move(args)),
        keep_sandbox_(keep_sandbox),
        stdout_(std::unique_ptr<FileID>(new FileID(
            store_directory_, "Standard output for " + description_))),
        stderr_(std::unique_ptr<FileID>(new FileID(
            store_directory_, "Standard error for " + description_))),
        cacher_(cacher) {
    callback_ = [](const TaskStatus& status) {
      return status.event != TaskStatus::FAILURE;
    };
  }

  std::string store_directory_;
  std::string temp_directory_;
  int num_cores_;

  std::string description_;
  int64_t id_;
  static std::atomic<int32_t> next_id_;

  std::string executable_;
  std::vector<std::string> args_;
  bool keep_sandbox_;
  std::unordered_map<std::string, int64_t> inputs_;
  std::unordered_map<std::string, std::unique_ptr<FileID>> outputs_;

  int64_t stdin_ = 0;
  std::unique_ptr<FileID> stdout_;
  std::unique_ptr<FileID> stderr_;

  bool successful_ = false;
  std::string message_;
  bool exclusive_ = false;
  CachingMode caching_mode_ = ALWAYS;
  std::string executor_;

  ExecutionCacher* cacher_;
  bool cached_ = false;

  proto::Response response_;
  proto::Resources resource_limits_;

  std::function<bool(const TaskStatus&)> callback_;
};

}  // namespace core
#endif
