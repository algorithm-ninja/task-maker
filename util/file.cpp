#include "util/file.hpp"
#include "glog/logging.h"
#include "util/sha256.hpp"

#include <cstdlib>

#include <fstream>
#include <system_error>

#if defined(__unix__) || defined(__linux__) || defined(__APPLE__)
#include <fcntl.h>
#include <ftw.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {

const constexpr char* kPathSeparators = "/";

bool MkDir(const std::string& dir) {
  return mkdir(dir.c_str(), S_IRWXU | S_IRWXG | S_IXOTH) != -1 ||
         errno == EEXIST;
}

bool OsRemove(const std::string& path) { return remove(path.c_str()) == -1; }

bool OsRemoveTree(const std::string& path) {
  return nftw(path.c_str(),
              [](const char* fpath, const struct stat* sb, int typeflags,
                 struct FTW* ftwbuf) { return remove(fpath); },
              64, FTW_DEPTH | FTW_PHYS | FTW_MOUNT) != -1;
}

bool OsMakeExecutable(const std::string& path) {
  return chmod(path.c_str(), S_IRUSR | S_IXUSR) != -1;
}

const size_t max_path_len = 1 << 15;
std::string OsTempDir(const std::string& path) {
  std::string tmp = util::File::JoinPath(path, "XXXXXX");
  CHECK_LT(tmp.size(), max_path_len);
  char data[max_path_len + 1];
  data[0] = 0;
  strncat(data, tmp.c_str(), max_path_len);  // NOLINT
  if (mkdtemp(data) == nullptr)              // NOLINT
    return "";
  return data;  // NOLINT
}

int OsTempFile(const std::string& path, std::string* tmp) {
#ifdef __APPLE__
  *tmp = path + ".";
  do {
    *tmp += 'a' + rand() % 26;
    int fd =
        open(tmp->c_str(), O_WRONLY | O_CREAT | O_CLOEXEC, S_IRUSR | S_IWUSR);
    if (fd == -1 && errno == EEXIST) continue;
    return fd;
  } while (true);
#else
  *tmp = path + ".XXXXXX";
  char data[max_path_len];
  data[0] = 0;
  strncat(data, tmp->c_str(), max_path_len);  // NOLINT
  int fd = mkostemp(data, O_CLOEXEC);         // NOLINT
  *tmp = data;                                // NOLINT
  return fd;
#endif
}

// Returns errno, or 0 on success.
int OsAtomicMove(const std::string& src, const std::string& dst,
                 bool overwrite = false, bool exist_ok = true) {
  // This may not have the desired effect if src is a symlink.
  if (overwrite) {
    if (rename(src.c_str(), dst.c_str()) == -1) return errno;
    return 0;
  }
  if (link(src.c_str(), dst.c_str()) == -1) {
    if (!exist_ok || errno != EEXIST) return errno;
    return 0;
  }
  if (remove(src.c_str()) == -1) return errno != ENOENT ? errno : 0;
  return 0;
}

int OsRead(const std::string& path,
           const util::File::ChunkReceiver& chunk_receiver) {
  int fd = open(path.c_str(), O_CLOEXEC | O_RDONLY);  // NOLINT
  if (fd == -1) return errno;
  ssize_t amount;
  proto::FileContents contents;
  try {
    char buf[util::kChunkSize] = {};
    while ((amount = read(fd, buf, util::kChunkSize))) {  // NOLINT
      if (amount == -1 && errno == EINTR) continue;
      if (amount == -1) break;
      contents.set_chunk(buf, amount);  // NOLINT
      chunk_receiver(contents);
    }
  } catch (...) {
    close(fd);
    throw;
  }
  if (amount == -1) {
    int error = errno;
    close(fd);
    return error;
  }
  return close(fd) == -1 ? errno : 0;
}

int OsWrite(const std::string& path,
            const util::File::ChunkProducer& chunk_producer, bool overwrite,
            bool exist_ok) {
  std::string temp_file;
  int fd = OsTempFile(path, &temp_file);
  if (fd == -1) return errno;
  try {
    chunk_producer([&fd, &temp_file](const proto::FileContents& chunk) {
      size_t pos = 0;
      while (pos < chunk.chunk().size()) {
        ssize_t written = write(fd, chunk.chunk().c_str() + pos,  // NOLINT
                                chunk.chunk().size() - pos);
        if (written == -1 && errno == EINTR) continue;
        if (written == -1) {
          throw std::system_error(errno, std::system_category(),
                                  "write " + temp_file);
        }
        pos += written;
      }
    });
  } catch (...) {
    close(fd);
    throw;
  }
  if (close(fd) == -1) return errno;
  return OsAtomicMove(temp_file, path, overwrite, exist_ok);
}

}  // namespace
#endif

namespace util {

void File::Read(const std::string& path,
                const File::ChunkReceiver& chunk_receiver) {
  int err = OsRead(path, chunk_receiver);
  if (err != 0)
    throw std::system_error(err, std::system_category(), "Read " + path);
}

void File::Write(const std::string& path, const ChunkProducer& chunk_producer,
                 bool overwrite, bool exist_ok) {
  MakeDirs(BaseDir(path));
  if (!overwrite && Size(path) >= 0) {
    if (exist_ok) return;
    throw std::system_error(EEXIST, std::system_category(), "Write " + path);
  }
  int err = OsWrite(path, chunk_producer, overwrite, exist_ok);
  if (err != 0) throw std::system_error(err, std::system_category(), path);
}

SHA256_t File::Hash(const std::string& path) {
  SHA256 hasher;
  Read(path, [&hasher](const proto::FileContents& chunk) {
    hasher.update(reinterpret_cast<const unsigned char*>(chunk.chunk().data()),
                  chunk.chunk().size());
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

void File::Copy(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  using std::placeholders::_1;
  Write(to, std::bind(Read, from, _1), overwrite, exist_ok);
}

void File::Move(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  if (OsAtomicMove(from, to, overwrite, exist_ok) == 0) {
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

void File::MakeExecutable(const std::string& path) {
  if (!OsMakeExecutable(path))
    throw std::system_error(errno, std::system_category(), "chmod");
}

std::string File::PathForHash(const SHA256_t& hash) {
  std::string path = hash.Hex();
  return JoinPath(JoinPath(path.substr(0, 2), path.substr(2, 2)), path);
}

std::string File::JoinPath(const std::string& first,
                           const std::string& second) {
  if (strchr(kPathSeparators, second[0]) != nullptr) return second;
  return first + kPathSeparators[0] + second;  // NOLINT
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
  if (path_.empty())
    throw std::system_error(errno, std::system_category(), "mkdtemp");
}
void TempDir::Keep() { keep_ = true; }
const std::string& TempDir::Path() const { return path_; }
TempDir::~TempDir() {
  if (!keep_) File::RemoveTree(path_);
}

std::string File::SHAToPath(const std::string& store_directory,
                            const SHA256_t& hash) {
  return util::File::JoinPath(store_directory, util::File::PathForHash(hash));
}

std::string File::ProtoSHAToPath(const std::string& store_directory,
                                 const proto::SHA256& hash) {
  util::SHA256_t extracted_hash;
  ProtoToSHA256(hash, &extracted_hash);
  return SHAToPath(store_directory, extracted_hash);
}

void File::SetSHA(const std::string& store_directory, const SHA256_t& hash,
                  proto::FileInfo* dest) {
  util::SHA256ToProto(hash, dest->mutable_hash());
  dest->clear_contents();
  if (util::File::Size(SHAToPath(store_directory, hash)) <= util::kChunkSize) {
    util::File::Read(
        SHAToPath(store_directory, hash),
        [&dest](const proto::FileContents& bf) {
          if (!dest->contents().chunk().empty()) {
            throw std::runtime_error("Small file with more than one chunk");
          }
          *dest->mutable_contents() = bf;
        });
  }
}

}  // namespace util
