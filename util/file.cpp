#include "util/file.hpp"
#include "util/sha256.hpp"

#if defined(__unix__) || defined(__linux__) || defined(__apple__)
#include <sys/stat.h>
#include <sys/types.h>
#endif

#include <fstream>
#include <iostream>

namespace util {

namespace {
#if defined(__unix__) || defined(__linux__) || defined(__apple__)
void MkDir(const std::string& dir) {
  if (mkdir(dir.c_str(), S_IRWXU | S_IRWXG | S_IXOTH) == -1) {
    if (errno == EEXIST) return;
    throw std::system_error(errno, std::system_category(), "mkdir");
  }
}
#endif
}  // namespace

static const uint32_t kChunkSize = 32 * 1024;

void File::Read(const std::string& path,
                const File::ChunkReceiver& chunk_receiver) {
  std::ifstream fin;
  fin.exceptions(std::ifstream::failbit | std::ifstream::badbit);
  fin.open(path);
  proto::FileContents chunk;
  std::vector<char> buf(kChunkSize);
  size_t read_size = 0;
  while ((read_size = fin.readsome(buf.data(), kChunkSize)) != 0) {
    chunk.set_chunk(buf.data(), read_size);
    chunk_receiver(chunk);
  }
}

File::ChunkReceiver File::Write(const std::string& path) {
  using namespace std::placeholders;
  MakeDirs(path);
  auto fout = std::make_shared<std::ofstream>();
  fout->exceptions(std::ofstream::failbit | std::ofstream::badbit);
  fout->open(path);
  return [fout](const proto::FileContents& chunk) {
    fout->write(chunk.chunk().c_str(), chunk.chunk().size());
  };
}

SHA256_t File::Hash(const std::string& path) {
  SHA256 hasher;
  Read(path, [&hasher](const proto::FileContents& chunk) {
    hasher.update((unsigned char*)chunk.chunk().c_str(), chunk.chunk().size());
  });
  SHA256_t digest;
  hasher.finalize(&digest);
  return digest;
}

void File::MakeDirs(const std::string& path) {
  uint64_t pos = 0;
  while (true) {
    pos = path.find_first_of('/', pos + 1);
    if (pos == std::string::npos) break;
    MkDir(path.substr(0, pos));
  }
}

}  // namespace util
