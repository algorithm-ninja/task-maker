#ifndef SERVER_CACHE_HPP
#define SERVER_CACHE_HPP
#include <kj/std/iostream.h>
#include <fstream>
#include <map>
#include <unordered_map>
#include "server/dispatcher.hpp"
#include "util/sha256.hpp"

namespace server {
namespace detail {
struct RequestHasher {
  uint64_t operator()(capnproto::Request::Reader reader) const;
};
struct RequestComparator {
  bool operator()(capnproto::Request::Reader a,
                  capnproto::Request::Reader b) const;
};
}  // namespace detail
class CacheManager {
 public:
  CacheManager();
  bool Has(capnproto::Request::Reader req);
  capnproto::Result::Reader Get(capnproto::Request::Reader req);
  void Set(capnproto::Request::Reader req, capnproto::Result::Reader res);

 private:
  std::unordered_map<capnproto::Request::Reader, capnproto::Result::Reader,
                     detail::RequestHasher, detail::RequestComparator>
      data_;
  std::unordered_map<util::SHA256_t, size_t, util::SHA256_t::Hasher>
      file_sizes_;
  std::unordered_map<util::SHA256_t, size_t, util::SHA256_t::Hasher>
      file_access_times_;
  std::map<size_t, util::SHA256_t> sorted_files_;
  size_t total_size_ = 0;
  size_t last_access_time_ = 0;
  std::vector<kj::Own<capnp::MessageBuilder>> builders_;
  std::ofstream fout_;
  kj::std::StdOutputStream os_{fout_};

  static std::string Path();
};
}  // namespace server

#endif
