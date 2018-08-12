@0xb7014c96fc2e7e2a;
using import "sha256.capnp".SHA256;

interface FileReceiver {
  sendChunk @0 (chunk :Data);
}

interface FileSender {
  requestFile @0 (hash :SHA256, receiver :FileReceiver);
}
