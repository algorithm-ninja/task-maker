@0xe123d239ae4aa1fc;

using import "file.capnp".FileSender;
using import "sha256.capnp".SHA256;
using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("capnproto");

struct FileInfo {
  name @0 :Text; # Name, relative to the sandbox, of the file
  hash @1 :SHA256; # Hash of the contents
  executable @2 :Bool; # Marks the file as executable
}

struct FifoInfo {
  name @0 :Text;
  id @1 :UInt32;
}

struct Resources {
  # All times are in seconds, all sizes in kilobytes.
  cpuTime @0 :Float32;
  sysTime @1 :Float32;
  wallTime @2 :Float32;
  memory @3 :UInt64;

  # The following names correspond to RLIMIT_ names.
  nproc @4 :UInt32;
  nofiles @5 :UInt32;
  fsize @6 :UInt64;
  memlock @7 :UInt64;
  stack @8 :UInt64; # 0 means unlimited
}

struct ProcessRequest {
  executable :union {
    system@0 :Text;
    localFile @1 :FileInfo;
  }
  args @2 :List(Text);
  stdin :union {
    hash @3 :SHA256; # Hash of standard input
    fifo @4 :UInt32; # ID of the input FIFO
  }
  stdout @5 :UInt32; # ID of the stdout FIFO
  stderr @6 :UInt32; # ID of the stderr FIFO
  inputFiles @7 :List(FileInfo); # Name and hash of other inputs
  outputFiles @8 :List(Text); # Name of outputs
  fifos @9 :List(FifoInfo); # Name and ID of FIFOs
  limits @10 :Resources;
  extraTime @11 :Float32; # Time that should be added to the cpu time limit.
}

struct Request {
  processes @0 :List(ProcessRequest);
  exclusive @1 :Bool; # If set, no other execution should run at the same time.
}

struct ProcessResult {
  status :union {
    success @0 :Void;
    signal @1 :UInt32;
    returnCode @2 :UInt32;
    timeLimit @3 :Void;
    wallLimit @4 :Void;
    memoryLimit @5 :Void;
    missingFiles @6 :Void;
    invalidRequest @7 :Text;
    internalError @8 :Text;
  }
  resourceUsage @9 :Resources;
  stdout @10 :SHA256; # Hash of standard output
  stderr @11 :SHA256; # Hash of standard error
  outputFiles @12 :List(FileInfo); # Name and hash of other outputs
  wasKilled @13 :Bool; # True if the execution was killed by the sandbox. 
  wasCached @14 :Bool; # True if the answer comes from the cache.
}

struct Result {
  processes @0 :List(ProcessResult);
}

interface Evaluator extends(FileSender) {
  evaluate @0 (request :Request) -> (result :Result);
  id @1 () -> (text :Result);
}
