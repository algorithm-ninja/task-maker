#ifndef SERVER_CACHE_HPP
#define SERVER_CACHE_HPP
#include "server/dispatcher.hpp"

namespace server {
class CacheManager {
 public:
  CacheManager() {}
  bool Has(capnproto::Request::Reader req);
  capnproto::Result::Reader Get(capnproto::Request::Reader req);
  void Set(capnproto::Request::Reader req, capnproto::Result::Reader res);

 private:
};
}  // namespace server

#endif
