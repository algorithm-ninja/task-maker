#ifndef UTIL_FILE_HPP
#define UTIL_FILE_HPP
#include <functional>

#include "proto/file.pb.h"
#include "util/sha256.hpp"

namespace util {

class File {
 public:
  using ChunkReceiver = std::function<void(const proto::FileContents&)>;

  // Reads the file specified by path in chunks.
  static void Read(const std::string& path,
                   const ChunkReceiver& chunk_receiver);

  // Returns a ChunkReceiver that writes the given data to a file.
  // The file is closed when the ChunkReceiver goes out of scope.
  static ChunkReceiver Write(const std::string& path);

  // Computes the hash of the file specified by path.
  static SHA256_t Hash(const std::string& path);

  // Creates all the folder that are needed to write the specified file
  // or, if path is a directory, creates all the folders.
  static void MakeDirs(const std::string& path);
};

}  // namespace util

#endif
