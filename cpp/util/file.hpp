#ifndef UTIL_FILE_HPP
#define UTIL_FILE_HPP
#include <memory>

#include <kj/common.h>
#include <kj/function.h>
#include "capnp/file.capnp.h"
#include "util/sha256.hpp"

namespace util {

static const constexpr uint32_t kChunkSize = 1024 * 1024;

class File {
 public:
  using Chunk = kj::ArrayPtr<const kj::byte>;
  using ChunkReceiver = kj::Function<void(Chunk)>;

  // Reads the file specified by path in chunks.
  static void Read(const std::string& path, ChunkReceiver chunk_receiver);

  // Returns a receiver that writes to the given file and finalizes
  // the write when destroyed.
  static kj::Maybe<ChunkReceiver> Write(const std::string& path,
                                        bool overwrite = false,
                                        bool exist_ok = true);

  // Computes the hash of the file specified by path.
  static SHA256_t Hash(const std::string& path);

  // Creates all the folder that are needed to write the specified file
  // or, if path is a directory, creates all the folders.
  static void MakeDirs(const std::string& path);

  // Copies from -> to.
  static void Copy(const std::string& from, const std::string& to,
                   bool overwrite = false, bool exist_ok = true);

  // Copies from -> to without using hard links.
  static void HardCopy(const std::string& from, const std::string& to,
                       bool overwrite = false, bool exist_ok = true);

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

  // Computes a file's size. Returns a negative number in case of errors.
  static int64_t Size(const std::string& path);

  // Returns true if a file exists
  static bool Exists(const std::string& path) { return Size(path) >= 0; }

  // Returns the storage path of a file with the given SHA.
  static std::string SHAToPath(const std::string& store_directory,
                               const SHA256_t& hash);

  // Utility to implement RequestFile methods, given the hash and the receiver
  static kj::Promise<void> HandleRequestFile(
      const util::SHA256_t& hash, capnproto::FileReceiver::Client receiver);

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
    Receiver(ChunkReceiver receiver) : receiver_(std::move(receiver)) {}
    Receiver(util::SHA256_t hash) {
      KJ_IF_MAYBE(tmp, Write(PathForHash(hash), /*overwrite=*/true)) {
        receiver_ = std::move(*tmp);
      }
    }
    kj::Promise<void> SendChunk(SendChunkContext context);

   private:
    ChunkReceiver receiver_;
  };

  // Retrieve a file from a FileSender and store it in storage
  static kj::Promise<void> Get(const util::SHA256_t& hash,
                               capnproto::FileSender::Client worker)
      KJ_WARN_UNUSED_RESULT {
    auto req = worker.requestFileRequest();
    hash.ToCapnp(req.initHash());
    req.setReceiver(kj::heap<util::File::Receiver>(hash));
    return req.send().ignoreResult();
  }

  // Same as Get, but skip zero files and already present files.
  static kj::Promise<void> MaybeGet(const util::SHA256_t& hash,
                                    capnproto::FileSender::Client worker)
      KJ_WARN_UNUSED_RESULT {
    if (hash.isZero()) return kj::READY_NOW;
    if (!util::File::Exists(util::File::PathForHash(hash))) {
      return Get(hash, worker);
    } else {
      return kj::READY_NOW;
    }
  }
};  // namespace util

class TempDir {
 public:
  explicit TempDir(const std::string& base);
  const std::string& Path() const;
  void Keep();
  ~TempDir();

  TempDir(TempDir&&) = default;
  TempDir& operator=(TempDir&&) = default;
  TempDir(const TempDir&) = delete;
  TempDir& operator=(const TempDir&) = delete;

 private:
  std::string path_;
  bool keep_ = false;
};

}  // namespace util

#endif
