@0xe123d239ae4aa1fc;

using import "file.capnp".FileSender;
using import "sha256.capnp".SHA256;

struct FileInfo {
  name @0 :Text; # Name, relative to the sandbox, of the file
  hash @1 :SHA256; # Hash of the contents
  executable @2 :Bool; # Marks the file as executable
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

struct Request {
  executable :union {
    absolutePath @0 :Text;
    localFile @1 :FileInfo;
  }
  args @2 :List(Text);
  stdin @3 :SHA256; # Hash of standard input
  inputFiles @4 :List(FileInfo); # Name and hash of other inputs
  outputFiles @5 :List(Text); # Name of outputs
  limits @6 :Resources;
  extraTime @7 :Float32; # Time that should be added to the cpu time limit.
  exclusive @8 :Bool; # If set, no other execution should run at the same time.

  # TODO: FIFOs
}

struct Result {
  status :union {
    success @0 :Void;
    signal @1 :UInt32;
    returnCode @2 :UInt32;
    timeLimit @3 :Void;
    memoryLimit @4 :Void;
    internalError @5 :Text;
  }
  resourceUsage @6 :Resources;
  stdout @7 :SHA256; # Hash of standard output
  stderr @8 :SHA256; # Hash of standard error
  outputFiles @9 :List(FileInfo); # Name and hash of other outputs
}

interface Evaluator extends(FileSender) {
  evaluate @0 (request :Request) -> (result :Result);
}
