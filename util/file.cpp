#include "util/file.hpp"
#include "util/flags.hpp"
#include "util/sha256.hpp"

#include <stdlib.h>

#include <fstream>

#if defined(__unix__) || defined(__linux__) || defined(__APPLE__)
#include <ftw.h>
#include <unistd.h>

namespace {

static const constexpr char* kPathSeparators = "/";

bool MkDir(const std::string& dir) {
  return mkdir(dir.c_str(), S_IRWXU | S_IRWXG | S_IXOTH) != -1 ||
         errno == EEXIST;
}

bool OsRemove(const std::string& path) { return remove(path.c_str()) == -1; }

// Best-effort implementation - in some conditions this may still
// fail to overwrite the file even if the flag is specified.
bool ShallowCopy(const std::string& from, const std::string& to,
                 bool overwrite = true, bool exist_ok = true) {
  if (overwrite) OsRemove(to);
  if (link(from.c_str(), to.c_str()) != -1) return true;
  if (!exist_ok) return false;
  return errno == EEXIST;
}

bool OsRemoveTree(const std::string& path) {
  return nftw(path.c_str(),
              [](const char* fpath, const struct stat* sb, int typeflags,
                 struct FTW* ftwbuf) { return remove(fpath); },
              64, FTW_DEPTH | FTW_PHYS | FTW_MOUNT) != -1;
}

std::string OsTempFile(const std::string& path) {
  std::string tmp = path + ".XXXXXX";
  std::unique_ptr<char[]> data{strdup(tmp.c_str())};
  int fd = mkstemp(data.get());
  if (fd == -1) {
    return "";
  }
  close(fd);
  return data.get();
}

std::string OsTempDir(const std::string& path) {
  std::string tmp = util::File::JoinPath(path, "XXXXXX");
  std::unique_ptr<char[]> data{strdup(tmp.c_str())};
  if (mkdtemp(data.get()) == nullptr) {
    return "";
  }
  return data.get();
}

bool OsAtomicMove(const std::string& src, const std::string& dst,
                  bool overwrite = false, bool exist_ok = true) {
  if (overwrite) {
    return rename(src.c_str(), dst.c_str()) != -1;
  }
  if (link(src.c_str(), dst.c_str()) == -1) {
    if (!exist_ok || errno != EEXIST) return false;
  }
  return remove(src.c_str()) != -1;
}

}  // namespace
#endif

namespace util {

void File::Read(const std::string& path,
                const File::ChunkReceiver& chunk_receiver) {
  std::ifstream fin;
  fin.exceptions(std::ifstream::badbit);
  fin.open(path);
  if (!fin) throw std::system_error(ENOENT, std::system_category(), path);
  proto::FileContents chunk;
  std::vector<char> buf(kChunkSize);
  while (!fin.eof()) {
    fin.read(buf.data(), kChunkSize);
    chunk.set_chunk(buf.data(), fin.gcount());
    chunk_receiver(chunk);
  }
}

void File::Write(const std::string& path, const ChunkProducer& chunk_producer,
                 bool overwrite, bool exist_ok) {
  MakeDirs(BaseDir(path));
  if (!overwrite && Size(path) >= 0) {
    if (exist_ok) return;
    throw std::system_error(EEXIST, std::system_category(), path);
  }
  std::ofstream fout;
  fout.exceptions(std::ofstream::failbit | std::ofstream::badbit);
  std::string temp_file_ = OsTempFile(path);
  if (temp_file_ == "")
    throw std::system_error(errno, std::system_category(), "mkstemp");
  fout.open(temp_file_);
  chunk_producer([&fout](const proto::FileContents& chunk) {
    fout.write(chunk.chunk().c_str(), chunk.chunk().size());
  });
  if (!OsAtomicMove(temp_file_, path, overwrite, exist_ok))
    throw std::system_error(errno, std::system_category(), path);
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
  while (pos != std::string::npos) {
    pos = path.find_first_of(kPathSeparators, pos + 1);
    if (!MkDir(path.substr(0, pos))) {
      throw std::system_error(errno, std::system_category(), "mkdir");
    }
  }
}

void File::DeepCopy(const std::string& from, const std::string& to,
                    bool overwrite, bool exist_ok) {
  using namespace std::placeholders;
  Write(to, std::bind(Read, from, _1), overwrite, exist_ok);
}

void File::Copy(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  if (!ShallowCopy(from, to, overwrite, exist_ok)) {
    DeepCopy(from, to, overwrite, exist_ok);
  }
}

void File::Move(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  if (!OsAtomicMove(from, to, overwrite, exist_ok)) {
    Copy(from, to, overwrite, exist_ok);
    Remove(from);
  }
}

void File::Remove(const std::string& path) {
  if (!OsRemove(path))
    throw std::system_error(errno, std::system_category(), "remove");
}

void File::RemoveTree(const std::string& path) {
  if (!OsRemoveTree(path))
    throw std::system_error(errno, std::system_category(), "removetree");
}

std::string File::PathForHash(const SHA256_t& hash) {
  std::string path = hash.Hex();
  return JoinPath(JoinPath(path.substr(0, 2), path.substr(2, 2)), path);
}

std::string File::JoinPath(const std::string& first,
                           const std::string& second) {
  if (strchr(kPathSeparators, second[0])) return second;
  return first + kPathSeparators[0] + second;
}

std::string File::BaseDir(const std::string& path) {
  return path.substr(0, path.find_last_of(kPathSeparators));
}

int64_t File::Size(const std::string& path) {
  std::ifstream fin(path, std::ios::ate | std::ios::binary);
  if (!fin) return -1;
  return fin.tellg();
}

TempDir::TempDir(const std::string& base) {
  path_ = OsTempDir(base);
  if (path_ == "")
    throw std::system_error(errno, std::system_category(), "mkdtemp");
}
void TempDir::Keep() { keep_ = true; }
const std::string& TempDir::Path() const { return path_; }
TempDir::~TempDir() {
  if (!keep_) File::RemoveTree(path_);
}

std::string File::SHAToPath(const SHA256_t& hash) {
  return util::File::JoinPath(FLAGS_store_directory,
                              util::File::PathForHash(hash));
}

std::string File::ProtoSHAToPath(const proto::SHA256& hash) {
  util::SHA256_t extracted_hash;
  ProtoToSHA256(hash, &extracted_hash);
  return SHAToPath(extracted_hash);
  return util::File::JoinPath(FLAGS_store_directory,
                              util::File::PathForHash(extracted_hash));
}

void File::SetSHA(const SHA256_t& hash, proto::FileInfo* dest) {
  util::SHA256ToProto(hash, dest->mutable_hash());
  dest->clear_contents();
  if (util::File::Size(SHAToPath(hash)) <= util::kChunkSize) {
    util::File::Read(SHAToPath(hash), [&dest](const proto::FileContents& bf) {
      if (dest->contents().chunk().size() != 0) {
        throw std::runtime_error("Small file with more than one chunk");
      }
      *dest->mutable_contents() = bf;
    });
  }
}

}  // namespace util
