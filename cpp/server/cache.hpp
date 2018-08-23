#ifndef SERVER_CACHE_HPP
#define SERVER_CACHE_HPP
#include <kj/std/iostream.h>
#include <fstream>
#include <unordered_map>
#include "server/dispatcher.hpp"

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
  std::vector<kj::Own<capnp::MessageBuilder>> builders_;
  std::ofstream fout_;
  kj::std::StdOutputStream os_{fout_};

  static std::string Path();
};
}  // namespace server

#endif
