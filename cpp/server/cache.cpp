#include "server/cache.hpp"
#include <capnp/message.h>
#include <kj/debug.h>
#include <algorithm>
#include "capnp/cache.capnp.h"
#include "util/sha256.hpp"

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
    case capnproto::Request::Executable::ABSOLUTE_PATH:
      hash_combine(hash, std::string(reader.getExecutable().getAbsolutePath()));
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
    case capnproto::Request::Executable::ABSOLUTE_PATH:
      if (a.getExecutable().getAbsolutePath() !=
          b.getExecutable().getAbsolutePath())
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
}  // namespace detail

CacheManager::CacheManager() {
  // TODO: read
}

bool CacheManager::Has(capnproto::Request::Reader req) {
  KJ_DBG("Has", req);
  return data_.count(req);
}
capnproto::Result::Reader CacheManager::Get(capnproto::Request::Reader req) {
  KJ_DBG("Get", req);
  return data_.at(req);
}
void CacheManager::Set(capnproto::Request::Reader req,
                       capnproto::Result::Reader res) {
  if (Has(req)) return;
  KJ_DBG("Set", req);
  builders_.push_back(kj::heap<capnp::MallocMessageBuilder>());
  auto entry = builders_.back()->getRoot<capnproto::CacheEntry>();
  entry.setRequest(req);
  entry.setResult(res);
  data_.emplace(entry.getRequest(), entry.getResult());
  // TODO: write
}

}  // namespace server
