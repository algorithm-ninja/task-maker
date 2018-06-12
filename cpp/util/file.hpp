#ifndef UTIL_FILE_HPP
#define UTIL_FILE_HPP
#include <functional>

#include "proto/file.pb.h"
#include "util/sha256.hpp"

namespace util {

static const constexpr uint32_t kChunkSize = 32 * 1024;

class File {
 public:
  using ChunkReceiver = std::function<void(const proto::FileContents&)>;
  using ChunkProducer = std::function<void(const ChunkReceiver&)>;

  // Reads the file specified by path in chunks.
  static void Read(const std::string& path,
                   const ChunkReceiver& chunk_receiver);

  // Takes as an argument a function that requires a chunk receiver, which is
  // called on a receiver that will output to the given file.
  static void Write(const std::string& path,
                    const ChunkProducer& chunk_producer, bool overwrite = false,
                    bool exist_ok = true);

  // Overload for writing directly a single chunk.
  static void Write(const std::string& path,
                    const proto::FileContents& contents, bool overwrite = false,
                    bool exist_ok = true) {
    Write(path,
          [&contents](const ChunkReceiver& chunk_receiver) {
            chunk_receiver(contents);
          },
          overwrite, exist_ok);
  }

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

  // Returns the storage path of a file with the given SHA.
  static std::string SHAToPath(const std::string& store_directory,
                               const SHA256_t& hash);
  static std::string ProtoSHAToPath(const std::string& store_directory,
                                    const proto::SHA256& hash);

  // Sets the SHA and possibly reads a small file.
  static void SetSHA(const std::string& store_directory, const SHA256_t& hash,
                     proto::FileInfo* dest);
};

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
