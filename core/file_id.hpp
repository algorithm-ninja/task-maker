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

  // These methods should be called after Core::Run is done.
  void WriteTo(const std::string& path);
  std::string Contents(int64_t size_limit = 0);

  FileID(FileID&& other) = default;
  FileID& operator=(FileID&& other) = default;
  ~FileID() = default;

 private:
  friend class Core;
  friend class Execution;

  FileID(const FileID& other) = default;
  FileID& operator=(const FileID& other) = default;

  explicit FileID(std::string description)
      : description_(std::move(description)), id_(next_id_++) {}
  FileID(std::string description, std::string path)
      : FileID(std::move(description)) {
    path_ = std::move(path);
  }

  bool Load(
      const std::function<void(int64_t, const util::SHA256_t&)>& set_hash);
  int64_t Id() const { return id_; }

  std::string description_;
  std::string path_;
  int64_t id_;
  util::SHA256_t hash_ = {};

  static std::atomic<int64_t> next_id_;
};

}  // namespace core
#endif
