@0xe2fea2013d38f4d2;
using import "evaluation.capnp".Request;
using import "evaluation.capnp".Result;
using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("capnproto");

struct CacheEntry {
  request @0 :Request;
  result @1 :Result;
}
