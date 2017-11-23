#ifndef UTIL_FILE_HPP
#define UTIL_FILE_HPP
#include <functional>

#include "proto/file.pb.h"
#include "util/sha256.hpp"

namespace util {

class File {
 public:
  using ChunkReceiver = std::function<void(const proto::FileContents&)>;
  static void Write(const std::string& path,
                    const ChunkReceiver& chunk_receiver);
  static ChunkReceiver Read(const std::string& path);
  static SHA256_t Hash(const std::string& path);
};

}  // namespace util

#endif
