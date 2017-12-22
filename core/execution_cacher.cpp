#include "core/execution_cacher.hpp"

#include <fstream>
#include <system_error>

#include "google/protobuf/util/message_differencer.h"
#include "proto/cache_entry.pb.h"
#include "util/file.hpp"
#include "util/sha256.hpp"

namespace core {

namespace {
template <class T>
inline size_t hash_combine(std::size_t seed, const T& v) {
  std::hash<T> hasher;
  seed ^= hasher(v) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
  return seed;
}

}  // namespace

namespace internal {
std::size_t RequestHasher::operator()(const proto::Request& request) const {
  size_t hash = 0;
  hash = hash_combine(hash, request.executable());
  for (const std::string& arg : request.arg()) {
    hash = hash_combine(hash, arg);
  }
  for (const auto& input : request.input()) {
    hash = hash_combine(hash, static_cast<int>(input.type()));
    hash = hash_combine(hash, input.name());
    util::SHA256_t sha;
    ProtoToSHA256(input.hash(), &sha);
    hash = hash_combine(hash, sha.Hex());
  }
  for (const auto& output : request.output()) {
    hash = hash_combine(hash, static_cast<int>(output.type()));
    hash = hash_combine(hash, output.name());
  }
  // TODO(veluca): FIFOs
  hash = hash_combine(hash, request.resource_limit().cpu_time());
  hash = hash_combine(hash, request.resource_limit().wall_time());
  hash = hash_combine(hash, request.resource_limit().memory());
  hash = hash_combine(hash, request.resource_limit().processes());
  hash = hash_combine(hash, request.resource_limit().nfiles());
  hash = hash_combine(hash, request.resource_limit().fsize());
  hash = hash_combine(hash, request.resource_limit().mlock());
  hash = hash_combine(hash, request.resource_limit().stack());
  hash = hash_combine(hash, request.exclusive());
  return hash;
}

bool RequestComparator::operator()(const proto::Request& first,
                                   const proto::Request& second) const {
  return google::protobuf::util::MessageDifferencer::Equals(first, second);
}
}  // namespace internal

bool ExecutionCacher::Get(const proto::Request& request,
                          const std::string& for_executor,
                          proto::Response* response) const {
  proto::Request key_request = request;
  for (auto& input : *key_request.mutable_input()) input.clear_contents();
  {
    std::lock_guard<std::mutex> lck(cache_mutex_);
    if (!cache_.count(for_executor)) return false;
    if (!cache_.at(for_executor).count(key_request)) return false;
    response->CopyFrom(cache_.at(for_executor).at(key_request));
  }
  for (const proto::FileInfo& out : response->output()) {
    std::string path = util::File::ProtoSHAToPath(store_directory_, out.hash());
    // Do not use this cached response if the output files cannot be found.
    if (util::File::Size(path) < 0) return false;
  }
  return true;
}

void ExecutionCacher::Put(const proto::Request& request,
                          const std::string& for_executor,
                          const proto::Response& response) {
  std::lock_guard<std::mutex> lck(cache_mutex_);
  proto::Request key_request = request;
  for (auto& input : *key_request.mutable_input()) input.clear_contents();
  cache_[for_executor][key_request] = response;
  for (auto& output : *cache_[for_executor][key_request].mutable_output())
    output.clear_contents();
}

void ExecutionCacher::Setup() {
  util::File::MakeDirs(store_directory_);
  path_ = util::File::JoinPath(store_directory_, "cache");
  std::ifstream fin(path_);
  if (!fin) return;
  proto::CacheData data;
  data.ParseFromIstream(&fin);
  for (const auto& entry : data.entry()) {
    cache_[entry.executor()][entry.request()] = entry.response();
  }
}

void ExecutionCacher::TearDown() {
  std::ofstream fout(path_);
  proto::CacheData data;
  for (const auto& executor : cache_) {
    for (const auto& req_resp : executor.second) {
      proto::CacheEntry* entry = data.add_entry();
      entry->set_executor(executor.first);
      entry->mutable_request()->CopyFrom(req_resp.first);
      entry->mutable_response()->CopyFrom(req_resp.second);
    }
  }
  data.SerializeToOstream(&fout);
}
}  // namespace core
