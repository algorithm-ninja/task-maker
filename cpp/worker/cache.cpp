#include "worker/cache.hpp"
#include "util/file.hpp"
#include "util/flags.hpp"

namespace worker {

Cache::Cache() {
  for (auto path : util::File::ListFiles(Flags::store_directory)) {
    try {
      util::SHA256_t hash(util::File::BaseName(path));
      KJ_ASSERT(util::File::PathForHash(hash) == path, hash.Hex(), path);
      size_t fsz = util::File::Size(path);
      if (!file_sizes_.count(hash)) {
        file_sizes_.emplace(hash, fsz);
        total_size_ += fsz;
      }
      file_access_times_[hash] = last_access_time_++;
    } catch (std::invalid_argument& e) {
      continue;
    }
  }
  for (auto kv : file_access_times_) {
    sorted_files_.emplace(kv.second, kv.first);
  }
}

void Cache::Register(util::SHA256_t hash) {
  if (hash.isZero()) return;
  if (!file_sizes_.count(hash)) {
    size_t sz = util::File::Size(util::File::PathForHash(hash));
    total_size_ += sz;
    file_sizes_.emplace(hash, sz);
  } else {
    sorted_files_.erase(file_access_times_.at(hash));
  }
  file_access_times_[hash] = last_access_time_++;
  sorted_files_.emplace(file_access_times_[hash], hash);
  while (Flags::cache_size != 0 &&
         total_size_ > 1024ULL * 1024 * Flags::cache_size) {
    KJ_ASSERT(!sorted_files_.empty());
    auto to_del = sorted_files_.begin()->second;
    try {
      util::File::Remove(util::File::PathForHash(to_del));
    } catch (...) {
      // If we could not remove the file, skip shrinking the cache.
      break;
    }
    sorted_files_.erase(sorted_files_.begin());
    total_size_ -= file_sizes_.at(to_del);
    file_sizes_.erase(to_del);
    file_access_times_.erase(to_del);
  }
  KJ_ASSERT(file_sizes_.count(hash), "Cache size is too small!");
}

}  // namespace worker
