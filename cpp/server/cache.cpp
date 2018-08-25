#include "server/cache.hpp"
#include <capnp/message.h>
#include <capnp/serialize.h>
#include <kj/debug.h>
#include <algorithm>
#include <fstream>
#include "capnp/cache.capnp.h"
#include "util/file.hpp"
#include "util/flags.hpp"

namespace server {
namespace detail {
template <class T>
inline void hash_combine(std::size_t& hash, const T& v) {
  std::hash<T> hasher;
  hash ^= hasher(v) + 0x9e3779b9 + (hash << 6) + (hash >> 2);
}

uint64_t RequestHasher::operator()(capnproto::Request::Reader reader) const {
  size_t hash = 0;
  hash_combine(hash, reader.getExecutable().which());
  switch (reader.getExecutable().which()) {
    case capnproto::Request::Executable::SYSTEM:
      hash_combine(hash, std::string(reader.getExecutable().getSystem()));
      break;
    case capnproto::Request::Executable::LOCAL_FILE:
      hash_combine(
          hash, std::string(reader.getExecutable().getLocalFile().getName()));
      hash_combine(
          hash, util::SHA256_t(reader.getExecutable().getLocalFile().getHash())
                    .Hex());
      break;
  }
  for (std::string arg : reader.getArgs()) {
    hash_combine(hash, arg);
  }
  hash_combine(hash, util::SHA256_t(reader.getStdin()).Hex());
  for (auto in : reader.getInputFiles()) {
    hash_combine(hash, std::string(in.getName()));
    hash_combine(hash, util::SHA256_t(in.getHash()).Hex());
    hash_combine(hash, in.getExecutable());
  }
  for (std::string out : reader.getOutputFiles()) {
    hash_combine(hash, out);
  }
  hash_combine(hash, reader.getLimits().getCpuTime());
  hash_combine(hash, reader.getLimits().getWallTime());
  hash_combine(hash, reader.getLimits().getMemory());
  hash_combine(hash, reader.getLimits().getNproc());
  hash_combine(hash, reader.getLimits().getNofiles());
  hash_combine(hash, reader.getLimits().getFsize());
  hash_combine(hash, reader.getLimits().getMemlock());
  hash_combine(hash, reader.getLimits().getStack());
  hash_combine(hash, reader.getExclusive());
  hash_combine(hash, reader.getExtraTime());
  return hash;
}
bool RequestComparator::operator()(capnproto::Request::Reader a,
                                   capnproto::Request::Reader b) const {
  if (a.getExecutable().which() != b.getExecutable().which()) return false;
  switch (a.getExecutable().which()) {
    case capnproto::Request::Executable::SYSTEM:
      if (a.getExecutable().getSystem() != b.getExecutable().getSystem())
        return false;
      break;
    case capnproto::Request::Executable::LOCAL_FILE:
      if (a.getExecutable().getLocalFile().getName() !=
          b.getExecutable().getLocalFile().getName())
        return false;
      if (util::SHA256_t(a.getExecutable().getLocalFile().getHash()).Hex() !=
          util::SHA256_t(b.getExecutable().getLocalFile().getHash()).Hex())
        return false;
      break;
  }
  auto aargs = a.getArgs();
  auto bargs = b.getArgs();
  for (size_t i = 0; i < aargs.size(); i++) {
    if (aargs[i] != bargs[i]) return false;
  }
  if (util::SHA256_t(a.getStdin()).Hex() != util::SHA256_t(b.getStdin()).Hex())
    return false;
  std::vector<std::tuple<std::string, std::string, bool>> ainput;
  std::vector<std::tuple<std::string, std::string, bool>> binput;
  for (auto in : a.getInputFiles()) {
    ainput.emplace_back(in.getName(), util::SHA256_t(in.getHash()).Hex(),
                        in.getExecutable());
  }
  for (auto in : b.getInputFiles()) {
    binput.emplace_back(in.getName(), util::SHA256_t(in.getHash()).Hex(),
                        in.getExecutable());
  }
  std::sort(ainput.begin(), ainput.end());
  std::sort(binput.begin(), binput.end());
  if (ainput != binput) return false;
  std::vector<std::string> aoutput;
  std::vector<std::string> boutput;
  for (auto out : a.getOutputFiles()) {
    aoutput.emplace_back(out);
  }
  for (auto out : b.getOutputFiles()) {
    boutput.emplace_back(out);
  }
  std::sort(aoutput.begin(), aoutput.end());
  std::sort(boutput.begin(), boutput.end());
  if (aoutput != boutput) return false;
  if (a.getLimits().getCpuTime() != b.getLimits().getCpuTime()) return false;
  if (a.getLimits().getWallTime() != b.getLimits().getWallTime()) return false;
  if (a.getLimits().getMemory() != b.getLimits().getMemory()) return false;
  if (a.getLimits().getNproc() != b.getLimits().getNproc()) return false;
  if (a.getLimits().getNofiles() != b.getLimits().getNofiles()) return false;
  if (a.getLimits().getFsize() != b.getLimits().getFsize()) return false;
  if (a.getLimits().getMemory() != b.getLimits().getMemory()) return false;
  if (a.getLimits().getStack() != b.getLimits().getStack()) return false;
  if (a.getExclusive() != b.getExclusive()) return false;
  if (a.getExtraTime() != b.getExtraTime()) return false;
  return true;
}

std::vector<util::SHA256_t> Hashes(capnproto::Request::Reader req,
                                   capnproto::Result::Reader res) {
  std::vector<util::SHA256_t> ans;
  auto add = [&ans](util::SHA256_t hash) {
    if (!hash.isZero()) ans.push_back(hash);
  };
  add(req.getStdin());
  if (req.getExecutable().isLocalFile())
    add(req.getExecutable().getLocalFile().getHash());
  for (auto f : req.getInputFiles()) add(f.getHash());
  add(res.getStdout());
  add(res.getStderr());
  for (auto f : res.getOutputFiles()) add(f.getHash());
  return ans;
};

}  // namespace detail

CacheManager::CacheManager() {
  std::ifstream fin(Path());
  if (fin) {
    kj::std::StdInputStream is(fin);
    while (true) {
      try {
        builders_.push_back(kj::heap<capnp::MallocMessageBuilder>());
        capnp::readMessageCopy(is, *builders_.back());
        auto entry = builders_.back()->getRoot<capnproto::CacheEntry>();
        bool missing_files = false;
        for (auto hash :
             detail::Hashes(entry.getRequest(), entry.getResult())) {
          int64_t fsz;
          if ((fsz = util::File::Size(util::File::PathForHash(hash))) < 0) {
            missing_files = true;
            break;
          }
        }
        if (missing_files) continue;
        for (auto hash :
             detail::Hashes(entry.getRequest(), entry.getResult())) {
          size_t fsz = util::File::Size(util::File::PathForHash(hash));
          if (!file_sizes_.count(hash)) {
            file_sizes_.emplace(hash, fsz);
            total_size_ += fsz;
          }
          file_access_times_[hash] = last_access_time_++;
        }
        for (auto kv : file_access_times_) {
          sorted_files_.emplace(kv.second, kv.first);
        }
        data_.emplace(entry.getRequest(), entry.getResult());
      } catch (kj::Exception& exc) {
        break;
      }
    }
    fin.close();
  }
  fout_.open(Path(), std::ios_base::out | std::ios_base::app);
}

bool CacheManager::Has(capnproto::Request::Reader req) {
  if (!data_.count(req)) return false;
  for (auto hash : detail::Hashes(req, data_.at(req))) {
    if (!file_sizes_.count(hash)) return false;
  }
  return true;
}

capnproto::Result::Reader CacheManager::Get(capnproto::Request::Reader req) {
  for (auto hash : detail::Hashes(req, data_.at(req))) {
    sorted_files_.erase(file_access_times_.at(hash));
    file_access_times_[hash] = last_access_time_++;
    sorted_files_.emplace(file_access_times_[hash], hash);
  }
  return data_.at(req);
}

void CacheManager::Set(capnproto::Request::Reader req,
                       capnproto::Result::Reader res) {
  if (Has(req)) return;
  for (auto hash : detail::Hashes(req, res)) {
    if (!file_sizes_.count(hash)) {
      size_t sz = util::File::Size(util::File::PathForHash(hash));
      total_size_ += sz;
      file_sizes_.emplace(hash, sz);
    } else {
      sorted_files_.erase(file_access_times_.at(hash));
    }
    file_access_times_[hash] = last_access_time_++;
    sorted_files_.emplace(file_access_times_[hash], hash);
  }
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
  for (auto hash : detail::Hashes(req, res)) {
    KJ_ASSERT(file_sizes_.count(hash), "Cache size is too small!");
  }
  builders_.push_back(kj::heap<capnp::MallocMessageBuilder>());
  auto entry = builders_.back()->getRoot<capnproto::CacheEntry>();
  entry.setRequest(req);
  entry.setResult(res);
  data_.emplace(entry.getRequest(), entry.getResult());
  capnp::writeMessage(os_, *builders_.back());
  fout_.flush();
}

std::string CacheManager::Path() {
  return util::File::JoinPath(Flags::store_directory, "cache");
}

}  // namespace server
