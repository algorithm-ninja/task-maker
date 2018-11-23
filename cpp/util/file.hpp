#ifndef UTIL_FILE_HPP
#define UTIL_FILE_HPP
#include <memory>

#include <kj/common.h>
#include <kj/debug.h>
#include <kj/function.h>
#include <vector>
#include "capnp/file.capnp.h"
#include "util/sha256.hpp"

namespace util {

static const constexpr uint32_t kChunkSize = 1024 * 1024;
static const constexpr uint32_t kInlineChunkThresh = 1024;

class File {
 public:
  // A non-owning pointer to a sequence of bytes, usually representing a part of
  // a file.
  using Chunk = kj::ArrayPtr<const kj::byte>;

  // A ChunkReceiver is a function that should be called one or more times with
  // a valid Chunk. An empty Chunk represents EOF.
  using ChunkReceiver = kj::Function<void(Chunk)>;

  // Subsequent calls to this function produce consecutive Chunks from some
  // source. On EOF, an empty Chunk is returned.
  using ChunkProducer = kj::Function<Chunk()>;

  // Lists all the files in a directory.
  static std::vector<std::string> ListFiles(const std::string& path);

  // Reads the file specified by path in chunks.
  static ChunkProducer Read(const std::string& path);

  // Returns a receiver that writes to the given file, the file ends when an
  // empty chunk is received, and finalizes the write when destroyed.
  static ChunkReceiver Write(const std::string& path, bool overwrite = false,
                             bool exist_ok = true);

  // Computes the hash of the file specified by path.
  static SHA256_t Hash(const std::string& path);

  // Creates all the folders that are needed to write the specified file
  // or, if path is a directory, creates all the folders.
  static void MakeDirs(const std::string& path);

  // Copies from -> to.
  static void Copy(const std::string& from, const std::string& to,
                   bool overwrite = false, bool exist_ok = true);

  // Copies from -> to without using hard links.
  static void HardCopy(const std::string& from, const std::string& to,
                       bool overwrite = false, bool exist_ok = true,
                       bool make_dirs = true);

  // Moves a file to a new position. If overwrite is false and exist_ok
  // is true, the original file is deleted anyway.
  static void Move(const std::string& from, const std::string& to,
                   bool overwrite = false, bool exist_ok = true);

  // Removes a file.
  static void Remove(const std::string& path);

  // Recursively removes a tree.
  static void RemoveTree(const std::string& path);

  // Make a file executable
  static void MakeExecutable(const std::string& path);

  // Make a file immutable
  static void MakeImmutable(const std::string& path);

  // Computes the path for a file with the given hash.
  static std::string PathForHash(const SHA256_t& hash);

  // Joins two paths.
  static std::string JoinPath(const std::string& first,
                              const std::string& second);

  // Computes the directory name for a path
  static std::string BaseDir(const std::string& path);

  // Computes the file name for a path
  static std::string BaseName(const std::string& path);

  // Computes a file's size. Returns a negative number in case of errors.
  static int64_t Size(const std::string& path);

  // Returns true if a file exists
  static bool Exists(const std::string& path) { return Size(path) >= 0; }

  // Returns the storage path of a file with the given SHA.
  static std::string SHAToPath(const std::string& store_directory,
                               const SHA256_t& hash);

  // Utility to implement RequestFile methods, given the path and the receiver
  static kj::Promise<void> HandleRequestFile(
      const std::string& path, capnproto::FileReceiver::Client receiver);
  static kj::Promise<void> HandleRequestFile(
      const util::SHA256_t& hash, capnproto::FileReceiver::Client receiver) {
    if (hash.hasContents()) {
      auto req = receiver.sendChunkRequest();
      req.setChunk(hash.getContents());
      return req.send().ignoreResult().then([receiver]() mutable {
        return receiver.sendChunkRequest().send().ignoreResult();
      });
    }
    return HandleRequestFile(PathForHash(hash), receiver);
  }

  // Utility to implement RequestFile methods
  template <typename RequestFileContext>
  static kj::Promise<void> HandleRequestFile(RequestFileContext context) {
    auto hash = context.getParams().getHash();
    auto receiver = context.getParams().getReceiver();
    return HandleRequestFile(hash, receiver);
  }

  // Simple capnproto server implementation to receive a file
  class Receiver : public capnproto::FileReceiver::Server {
   public:
    explicit Receiver(ChunkReceiver receiver)
        : receiver_(std::move(receiver)) {}
    explicit Receiver(const util::SHA256_t& hash) {
      receiver_ = Write(PathForHash(hash), /*overwrite=*/true);
    }
    kj::Promise<void> sendChunk(SendChunkContext context) override;

   private:
    ChunkReceiver receiver_;
  };

  // Retrieve a file from a FileSender and store it in storage
  static kj::Promise<void> Get(const util::SHA256_t& hash,
                               capnproto::FileSender::Client worker)
      KJ_WARN_UNUSED_RESULT {
    if (hash.hasContents()) {
      auto tmp = Write(PathForHash(hash), /*overwrite=*/true);
      tmp(hash.getContents());
      tmp({});
      return kj::READY_NOW;
    }
    auto req = worker.requestFileRequest();
    hash.ToCapnp(req.initHash());
    req.setReceiver(kj::heap<util::File::Receiver>(hash));
    return req.send().ignoreResult().then([]() {}).eagerlyEvaluate(nullptr);
  }

  // Same as Get, but skip zero files and already present files.
  static kj::Promise<void> MaybeGet(const util::SHA256_t& hash,
                                    capnproto::FileSender::Client worker)
      KJ_WARN_UNUSED_RESULT {
    if (hash.isZero()) return kj::READY_NOW;
    if (!util::File::Exists(util::File::PathForHash(hash))) {
      return Get(hash, worker);
    }
    return kj::READY_NOW;
  }

  // Creates a ChunkReceiver that lazily calls f to do get the actual receiver.
  // This is useful to, for example, create a file for Write only after at least
  // a chunk has been received.
  static ChunkReceiver LazyChunkReceiver(kj::Function<ChunkReceiver()> f);
};

// Creates a temporary directory in a given folder. The folder will be
// (recursively) removed on destruction.
class TempDir {
 public:
  // base is the directory in which the temporary directory will be created.
  explicit TempDir(const std::string& base);

  // Returns the path of the temporary folder.
  const std::string& Path() const;

  // Disables automatic deletion of the folder.
  void Keep();

  ~TempDir();

  TempDir(TempDir&& other) noexcept { *this = std::move(other); }
  TempDir& operator=(TempDir&& other) noexcept {
    path_ = std::move(other.path_);
    keep_ = other.keep_;
    other.moved_ = true;
    return *this;
  }
  KJ_DISALLOW_COPY(TempDir);

 private:
  std::string path_;
  bool keep_ = false;
  bool moved_ = false;
};

}  // namespace util

#endif
