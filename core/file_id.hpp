#ifndef CORE_FILE_ID_HPP
#define CORE_FILE_ID_HPP
#include <atomic>
#include <functional>
#include <string>

#include "util/sha256.hpp"

namespace core {

class Core;
class Execution;

class FileID {
 public:
  const std::string& Description() const { return description_; }
  int64_t ID() const { return id_; }

  // These methods should be called after Core::Run is done.
  void WriteTo(const std::string& path);
  std::string Contents(int64_t size_limit = 0);

  FileID(FileID&& other) = delete;
  FileID& operator=(FileID&& other) = delete;
  FileID(const FileID& other) = delete;
  FileID& operator=(const FileID& other) = delete;
  ~FileID() = default;

 private:
  friend class Core;
  friend class Execution;

  explicit FileID(std::string description)
      : description_(std::move(description)),
        id_((reinterpret_cast<int64_t>(&next_id_) << 32) | (next_id_++)) {
    // fprintf(stderr, "generated id: %lu, next_id_ ptr: %p\n", id_, &next_id_);
  }
  FileID(std::string description, std::string path)
      : FileID(std::move(description)) {
    path_ = std::move(path);
  }

  void Load(
      const std::function<void(int64_t, const util::SHA256_t&)>& set_hash);

  std::string description_;
  std::string path_;
  int64_t id_;
  util::SHA256_t hash_ = {};

  static std::atomic<int32_t> next_id_;
};

}  // namespace core
#endif
