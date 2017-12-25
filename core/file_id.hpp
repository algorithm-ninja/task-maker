#ifndef CORE_FILE_ID_HPP
#define CORE_FILE_ID_HPP
#include <atomic>
#include <functional>
#include <string>

#include "core/task_status.hpp"
#include "util/sha256.hpp"

namespace core {

class Core;
class Execution;

class FileID {
 public:
  const std::string& Description() const { return description_; }
  int64_t ID() const { return id_; }

  void SetCallback(const std::function<bool(const TaskStatus& status)>& cb) {
    callback_ = cb;
  }

  // These methods should be called after Core::Run is done.
  void WriteTo(const std::string& path, bool overwrite = false,
               bool exist_ok = true);
  std::string Contents(int64_t size_limit = 0);

  FileID(FileID&& other) = delete;
  FileID& operator=(FileID&& other) = delete;
  FileID(const FileID& other) = delete;
  FileID& operator=(const FileID& other) = delete;
  ~FileID() = default;

 private:
  friend class Core;
  friend class Execution;

  explicit FileID(std::string store_directory, std::string description)
      : description_(std::move(description)),
        store_directory_(std::move(store_directory)),
        id_((reinterpret_cast<int64_t>(&next_id_) << 32) | (next_id_++)) {
    // fprintf(stderr, "generated id: %lu, next_id_ ptr: %p\n", id_, &next_id_);
    callback_ = [](const TaskStatus& status) {
      return status.event != TaskStatus::FAILURE;
    };
  }
  FileID(std::string store_directory, std::string description, std::string path)
      : FileID(std::move(store_directory), std::move(description)) {
    path_ = std::move(path);
  }

  void Load(
      const std::function<void(int64_t, const util::SHA256_t&)>& set_hash);

  std::string description_;
  std::string path_;
  std::string store_directory_;
  int64_t id_;
  util::SHA256_t hash_ = {};
  std::function<bool(const TaskStatus&)> callback_;

  static std::atomic<int32_t> next_id_;
};

}  // namespace core
#endif
