#include "util/file.hpp"
#include "util/flags.hpp"
#include "util/sha256.hpp"

#include <fstream>

#if defined(__unix__) || defined(__linux__) || defined(__APPLE__)
#include <ftw.h>
#include <unistd.h>

namespace {

static const constexpr char* kPathSeparators = "/";

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
              struct FTW* ftwbuf) {
             std::cerr << "Remove " << fpath << std::endl;
             return remove(fpath);
           },
           64, FTW_DEPTH | FTW_PHYS | FTW_MOUNT) == -1) {
    throw std::system_error(errno, std::system_category(), "removetree");
  }
}

std::string OsTempDir(const std::string& path) {
  std::string tmp = util::File::JoinPath(path, "XXXXXX");
  std::unique_ptr<char[]> data{strdup(tmp.c_str())};
  if (mkdtemp(data.get()) == nullptr) {
    throw std::system_error(errno, std::system_category(), "mkdtemp");
  }
  return data.get();
}

}  // namespace
#endif

namespace util {

void File::Read(const std::string& path,
                const File::ChunkReceiver& chunk_receiver) {
  std::ifstream fin;
  fin.exceptions(std::ifstream::badbit);
  fin.open(path);
  if (!fin) throw file_not_found(path);
  proto::FileContents chunk;
  std::vector<char> buf(kChunkSize);
  while (!fin.eof()) {
    fin.read(buf.data(), kChunkSize);
    chunk.set_chunk(buf.data(), fin.gcount());
    chunk_receiver(chunk);
  }
}

File::ChunkReceiver File::Write(const std::string& path, bool overwrite) {
  if (!overwrite && util::File::Size(path) >= 0)
    throw file_exists("File " + path + " exists");
  MakeDirs(BaseDir(path));
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
  while (pos != std::string::npos) {
    pos = path.find_first_of(kPathSeparators, pos + 1);
    MkDir(path.substr(0, pos));
  }
}

void File::DeepCopy(const std::string& from, const std::string& to,
                    bool overwrite) {
  Read(from, Write(to, overwrite));
}

void File::Copy(const std::string& from, const std::string& to,
                bool overwrite) {
  if (!overwrite && Size(to) >= 0) return;
  if (!ShallowCopy(from, to)) DeepCopy(from, to, overwrite);
}

void File::Move(const std::string& from, const std::string& to) {
  Copy(from, to);
  Remove(from);
}

void File::Remove(const std::string& path) { OsRemove(path); }

void File::RemoveTree(const std::string& path) { OsRemoveTree(path); }

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

TempDir::TempDir(const std::string& base) { path_ = OsTempDir(base); }
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
