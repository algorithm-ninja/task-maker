#include "core/file_id.hpp"
#include "util/file.hpp"
#include "util/flags.hpp"

namespace core {

std::atomic<int64_t> FileID::next_id_{1};

void FileID::WriteTo(const std::string& path) {
  util::File::Copy(util::File::SHAToPath(hash_), path);
}

std::string FileID::Contents(int64_t size_limit) {
  std::string ans;
  util::File::Read(util::File::SHAToPath(hash_),
                   [size_limit, &ans](const proto::FileContents& contents) {
                     if (size_limit && (int64_t)ans.size() > size_limit) {
                       throw std::runtime_error("File too big");
                     }
                     ans += contents.chunk();
                   });
  return ans;
}

void FileID::Load(
    const std::function<void(int64_t, const util::SHA256_t&)>& set_hash) {
  if (path_.size() == 0) {
    throw std::logic_error("Invalid call to FileID::Load");
  }
  hash_ = util::File::Hash(path_);
  util::File::Copy(path_, util::File::JoinPath(FLAGS_store_directory,
                                               util::File::PathForHash(hash_)));
  set_hash(ID(), hash_);
}

}  // namespace core
