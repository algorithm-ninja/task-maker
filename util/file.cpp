#include "util/file.hpp"
#include "util/sha256.hpp"

#include <fstream>
#include <iostream>

#if defined(__unix__) || defined(__linux__) || defined(__APPLE__)
#include <ftw.h>
#include <stdio.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace {

void MkDir(const std::string& dir) {
  if (mkdir(dir.c_str(), S_IRWXU | S_IRWXG | S_IXOTH) == -1) {
    if (errno == EEXIST) return;
    throw std::system_error(errno, std::system_category(), "mkdir");
  }
}

bool ShallowCopy(const std::string& from, const std::string& to) {
  return link(from.c_str(), to.c_str()) != -1;
}

void OsRemove(const std::string& path) {
  if (remove(path.c_str()) == -1) {
    throw std::system_error(errno, std::system_category(), "remove");
  }
}

void OsRemoveTree(const std::string& path) {
  if (nftw(path.c_str(),
           [](const char* fpath, const struct stat* sb, int typeflags,
              struct FTW* ftwbuf) { return remove(fpath); },
           64, FTW_DEPTH | FTW_PHYS | FTW_MOUNT) == -1) {
    throw std::system_error(errno, std::system_category(), "removetree");
  }
}

}  // namespace
#endif

namespace util {

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

void File::DeepCopy(const std::string& from, const std::string& to) {
  Read(from, Write(to));
}

void File::Copy(const std::string& from, const std::string& to) {
  if (!ShallowCopy(from, to)) DeepCopy(from, to);
}

void File::Move(const std::string& from, const std::string& to) {
  Copy(from, to);
  Remove(from);
}

void File::Remove(const std::string& path) { OsRemove(path); }

void File::RemoveTree(const std::string& path) { OsRemoveTree(path); }

}  // namespace util
