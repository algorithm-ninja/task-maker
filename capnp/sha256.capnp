@0x8d3d14b8bd2f17f4;
using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("capnproto");

struct SHA256 {
  data0 @0 :UInt64;
  data1 @1 :UInt64;
  data2 @2 :UInt64;
  data3 @3 :UInt64;
}
