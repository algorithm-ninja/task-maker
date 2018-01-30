#include "core/file_id.hpp"
#include "glog/logging.h"
#include "util/file.hpp"

namespace core {

std::atomic<int32_t> FileID::next_id_{1};

void FileID::WriteTo(const std::string& path, bool overwrite, bool exist_ok) {
  util::File::Copy(util::File::SHAToPath(store_directory_, hash_), path,
                   overwrite, exist_ok);
}

std::string FileID::Contents(int64_t size_limit) {
  std::string ans;
  std::string source_path;
  {
    absl::MutexLock lck(&hash_mutex_);
    CHECK(!hash_.isZero());
    source_path = util::File::SHAToPath(store_directory_, hash_);
  }
  util::File::Read(
      source_path, [size_limit, &ans](const proto::FileContents& contents) {
        if (size_limit != 0 && static_cast<int64_t>(ans.size()) > size_limit) {
          throw std::runtime_error("File too big");
        }
        ans += contents.chunk();
      });
  return ans;
}

void FileID::Load(
    const std::function<void(int64_t, const util::SHA256_t&)>& set_hash) {
  if (path_.empty()) {
    throw std::logic_error("Invalid call to FileID::Load");
  }
  {
    absl::MutexLock lck(&hash_mutex_);
    hash_ = util::File::Hash(path_);
    LOG(INFO) << "Loading file " << path_ << " into hash " << hash_.Hex();
    util::File::Copy(path_, util::File::SHAToPath(store_directory_, hash_));
  }
  set_hash(ID(), hash_);
}

void FileID::SetHash(const proto::SHA256& hash) {
  absl::MutexLock lck(&hash_mutex_);
  util::ProtoToSHA256(hash, &hash_);
}

}  // namespace core
