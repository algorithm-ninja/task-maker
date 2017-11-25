#ifndef CORE_EXECUTION_HPP
#define CORE_EXECUTION_HPP

#include <functional>
#include <unordered_map>
#include <vector>

#include "core/file_id.hpp"
#include "proto/response.pb.h"

namespace core {

class execution_failure : public std::runtime_error {
 public:
  execution_failure() : std::runtime_error("Execution failure") {}
};

class Execution {
 public:
  const std::string& Description() const { return description_; }

  void Stdin(const FileID& in) { stdin_ = in.Id(); }
  void Input(const std::string& name, const FileID& id) {
    inputs_.emplace(name, FileID(id));
  }

  const FileID& Stdout() { return stdout_; }
  const FileID& Stderr() { return stderr_; }
  const FileID& Output(const std::string& name) {
    return Output(name, name + " for " + Description());
  }

  const FileID& Output(const std::string& name, const std::string& description);

  void CpuLimit(float limit) { resource_limits_.set_cpu_time(limit); }
  void WallLimit(float limit) { resource_limits_.set_wall_time(limit); }
  void MemoryLimit(int64_t kb) { resource_limits_.set_memory(kb); }
  void ProcessLimit(int32_t limit) { resource_limits_.set_processes(limit); }
  void FileLimit(int32_t limit) { resource_limits_.set_nfiles(limit); }
  void FileSizeLimit(int64_t kb) { resource_limits_.set_fsize(kb); }
  void MemoryLockLimit(int64_t limit) { resource_limits_.set_mlock(limit); }
  void StackLimit(int64_t limit) { resource_limits_.set_stack(limit); }

  void DieOnError() { die_on_error_ = true; }
  void Exclusive() { exclusive_ = true; }

  // To be called after Core::Run().
  bool Success() const { return successful_; }
  float CpuTime() const { return response_.resource_usage().cpu_time(); }
  float SysTime() const { return response_.resource_usage().sys_time(); }
  float WallTime() const { return response_.resource_usage().wall_time(); }
  int64_t Memory() const { return response_.resource_usage().memory(); }

  int32_t StatusCode() const { return response_.status_code(); }
  int32_t Signal() const { return response_.signal(); }

 private:
  friend class Core;
  std::vector<int64_t> Deps() const;
  bool Run(const std::function<util::SHA256_t(int64_t)>& get_hash,
           const std::function<void(int64_t, const util::SHA256_t&)>& set_hash);

  bool IsExclusive() const { return exclusive_; }

  Execution(std::string description, std::string executable,
            std::vector<std::string> args)
      : description_(std::move(description)),
        executable_(std::move(executable)),
        args_(std::move(args)),
        stdout_("Standard output for " + description_),
        stderr_("Standard error for " + description_) {}

  std::string description_;

  std::string executable_;
  std::vector<std::string> args_;
  std::unordered_map<std::string, FileID> inputs_;
  std::unordered_map<std::string, FileID> outputs_;

  int64_t stdin_ = 0;
  FileID stdout_;
  FileID stderr_;

  bool die_on_error_ = false;
  bool successful_ = false;
  bool exclusive_ = false;

  proto::Response response_;
  proto::Resources resource_limits_;
};

}  // namespace core
#endif
