#include "server/cache.hpp"
#include <kj/debug.h>

namespace server {

bool CacheManager::Has(capnproto::Request::Reader req) {
  KJ_DBG("Cache request");
  return false;
}
capnproto::Result::Reader CacheManager::Get(capnproto::Request::Reader req) {
  //
}
void CacheManager::Set(capnproto::Request::Reader req,
                       capnproto::Result::Reader res) {}

}  // namespace server
