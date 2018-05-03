#ifndef CORE_EXECUTION_CACHE_HPP
#define CORE_EXECUTION_CACHE_HPP

#include <mutex>
#include <string>
#include <unordered_map>

#include "proto/request.pb.h"
#include "proto/response.pb.h"

namespace core {

namespace internal {
struct RequestHasher {
  std::size_t operator()(const proto::Request& request) const;
};
struct RequestComparator {
  bool operator()(const proto::Request& first,
                  const proto::Request& second) const;
};
}  // namespace internal

// This class implements a file-backed cache for requests and responses.
// Its methods are thread-safe. It uses file-based locking to avoid issues
// when using the cache from different instances (or processes). This
// implementation works only in UNIX-based environments.
class ExecutionCacher {
 public:
  bool Get(const proto::Request& request, const std::string& for_executor,
           proto::Response* response) const;
  bool Get(const proto::Request& request, proto::Response* response) {
    for (const auto& executor : cache_) {
      if (Get(request, executor.first, response)) {
        return true;
      }
    }
    return false;
  }
  void Put(const proto::Request& request, const std::string& for_executor,
           const proto::Response& response);

  void Setup();
  void TearDown();
  explicit ExecutionCacher(std::string store_directory)
      : store_directory_(std::move(store_directory)) {}
  ~ExecutionCacher() = default;
  ExecutionCacher(const ExecutionCacher&) = delete;
  ExecutionCacher(ExecutionCacher&&) = delete;
  ExecutionCacher operator=(const ExecutionCacher&) = delete;
  ExecutionCacher operator=(ExecutionCacher&&) = delete;

 private:
  using SingleExecutorCache =
      std::unordered_map<proto::Request, proto::Response,
                         internal::RequestHasher, internal::RequestComparator>;
  std::unordered_map<std::string, SingleExecutorCache> cache_;
  std::string path_;
  mutable std::mutex cache_mutex_;
  std::string store_directory_;
};

}  // namespace core

#endif
