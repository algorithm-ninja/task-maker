#include "util/file.hpp"
#include "util/flags.hpp"
#include "util/sha256.hpp"

#include <cstdlib>

#include <fstream>
#include <system_error>

#if defined(__unix__) || defined(__linux__) || defined(__APPLE__)
#include <fcntl.h>
#include <ftw.h>
#include <sys/stat.h>
#include <unistd.h>

// if REMOVE_ALSO_MOUNT_POINTS is set remove also the mount points mounted in
// the sandbox when cleaning
#ifdef REMOVE_ALSO_MOUNT_POINTS
#define NFTW_EXTRA_FLAGS 0
#else
#define NFTW_EXTRA_FLAGS FTW_MOUNT
#endif

#include <kj/debug.h>
#include <kj/exception.h>

namespace {

const constexpr char* kPathSeparators = "/";

bool MkDir(const std::string& dir) {
  return mkdir(dir.c_str(), S_IRWXU | S_IRWXG | S_IXOTH) != -1 ||
         errno == EEXIST;
}

bool OsRemove(const std::string& path) { return remove(path.c_str()) != -1; }

bool OsRemoveTree(const std::string& path) {
  return nftw(path.c_str(),
              [](const char* fpath, const struct stat* sb, int typeflags,
                 struct FTW* ftwbuf) { return remove(fpath); },
              64, FTW_DEPTH | FTW_PHYS | NFTW_EXTRA_FLAGS) != -1;
}

bool OsMakeExecutable(const std::string& path) {
  return chmod(path.c_str(), S_IRUSR | S_IXUSR) != -1;
}

bool OsMakeImmutable(const std::string& path) {
  return chmod(path.c_str(), S_IRUSR) != -1;
}

const size_t max_path_len = 1 << 15;
std::string OsTempDir(const std::string& path) {
  std::string tmp = util::File::JoinPath(path, "XXXXXX");
  KJ_REQUIRE(tmp.size() < max_path_len, tmp.size(), max_path_len,
             "Path too long");
  char data[max_path_len + 1];
  data[0] = 0;
  strncat(data, tmp.c_str(), max_path_len - 1);  // NOLINT
  if (mkdtemp(data) == nullptr)                  // NOLINT
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
  strncat(data, tmp->c_str(), max_path_len - 1);  // NOLINT
  int fd = mkostemp(data, O_CLOEXEC);             // NOLINT
  *tmp = data;                                    // NOLINT
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

bool OsIsLink(const std::string& path) {
  struct stat buf;
  if (lstat(path.c_str(), &buf) == -1) return false;
  return S_ISLNK(buf.st_mode);
}

// Returns errno, or 0 on success.
int OsAtomicCopy(const std::string& src, const std::string& dst,
                 bool overwrite = false, bool exist_ok = true) {
  if (link(src.c_str(), dst.c_str()) == -1) {
    if (errno != EEXIST) return errno;
    if (exist_ok) return 0;
    if (!overwrite) return errno;
    if (!OsRemove(dst)) return errno;
    if (link(src.c_str(), dst.c_str()) == -1) return errno;
    return 0;
  }
  return 0;
}

int OsRead(const std::string& path, util::File::ChunkReceiver& chunk_receiver) {
  int fd = open(path.c_str(), O_CLOEXEC | O_RDONLY);  // NOLINT
  if (fd == -1) return errno;
  ssize_t amount;
  try {
    kj::byte buf[util::kChunkSize] = {};
    while ((amount = read(fd, buf, util::kChunkSize))) {  // NOLINT
      if (amount == -1 && errno == EINTR) continue;
      if (amount == -1) break;
      chunk_receiver(util::File::Chunk(buf, amount));
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

util::File::ChunkReceiver OsWrite(const std::string& path, bool overwrite,
                                  bool exist_ok) {
  std::string temp_file;
  int fd = OsTempFile(path, &temp_file);

  if (fd == -1) {
    throw std::system_error(errno, std::system_category(), "Write " + path);
  }
  auto finalize = [=]() {
    KJ_LOG(INFO, "Finalizing " + path);
    if (fd == -1) return;
    if (fsync(fd) == -1 || close(fd) == -1 ||
        OsAtomicMove(temp_file, path, overwrite, exist_ok)) {
      kj::UnwindDetector detector;
      detector.catchExceptionsIfUnwinding([path]() {
        throw std::system_error(errno, std::system_category(), "Write " + path);
      });
    }
  };
  return [fd, temp_file, path,
          _ = kj::defer(std::move(finalize))](util::File::Chunk chunk) mutable {
    KJ_DBG("Chunk for ", path);
    if (fd == -1) return;
    size_t pos = 0;
    while (pos < chunk.size()) {
      ssize_t written = write(fd, chunk.begin() + pos,  // NOLINT
                              chunk.size() - pos);
      if (written == -1 && errno == EINTR) continue;
      if (written == -1) {
        close(fd);
        fd = -1;
        throw std::system_error(errno, std::system_category(),
                                "write " + temp_file);
      }
      pos += written;
    }
  };
}

}  // namespace
#endif

namespace util {

void File::Read(const std::string& path, File::ChunkReceiver chunk_receiver) {
  int err = OsRead(path, chunk_receiver);
  if (err != 0)
    throw std::system_error(err, std::system_category(), "Read " + path);
}

kj::Maybe<File::ChunkReceiver> File::Write(const std::string& path,
                                           bool overwrite, bool exist_ok) {
  MakeDirs(BaseDir(path));
  KJ_DBG(path, Size(path));
  if (!overwrite && Size(path) >= 0) {
    if (exist_ok) return nullptr;
    throw std::system_error(EEXIST, std::system_category(), "Write " + path);
  }
  return OsWrite(path, overwrite, exist_ok);
}

SHA256_t File::Hash(const std::string& path) {
  SHA256 hasher;
  Read(path, [&hasher](util::File::Chunk chunk) {
    hasher.update(chunk.begin(), chunk.size());
  });
  return hasher.finalize();
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

void File::HardCopy(const std::string& from, const std::string& to,
                    bool overwrite, bool exist_ok) {
  MakeDirs(BaseDir(to));
  KJ_IF_MAYBE(receiver, Write(to, overwrite, exist_ok)) {
    Read(from, std::move(*receiver));
  }
}

void File::Copy(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  MakeDirs(BaseDir(to));
  if (OsIsLink(from) || OsAtomicCopy(from, to, overwrite, exist_ok)) {
    KJ_IF_MAYBE(receiver, Write(to, overwrite, exist_ok)) {
      Read(from, std::move(*receiver));
    }
  }
}

void File::Move(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  if (OsIsLink(from) || !OsAtomicMove(from, to, overwrite, exist_ok)) {
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

void File::MakeImmutable(const std::string& path) {
  if (!OsMakeImmutable(path))
    throw std::system_error(errno, std::system_category(), "chmod");
}

std::string File::PathForHash(const SHA256_t& hash) {
  std::string path = hash.Hex();
  return JoinPath(
      Flags::store_directory,
      JoinPath(JoinPath(path.substr(0, 2), path.substr(2, 2)), path));
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
  File::MakeDirs(base);
  path_ = OsTempDir(base);
  if (path_.empty())
    throw std::system_error(errno, std::system_category(), "mkdtemp");
}
void TempDir::Keep() { keep_ = true; }
const std::string& TempDir::Path() const { return path_; }
TempDir::~TempDir() {
  if (!keep_ && !moved_) File::RemoveTree(path_);
}

std::string File::SHAToPath(const std::string& store_directory,
                            const SHA256_t& hash) {
  return util::File::JoinPath(store_directory, util::File::PathForHash(hash));
}

kj::Promise<void> File::Receiver::SendChunk(SendChunkContext context) {
  KJ_DBG("send_chunk");
  receiver_(context.getParams().getChunk());
  return kj::READY_NOW;
}

kj::Promise<void> File::HandleRequestFile(
    const util::SHA256_t& hash, capnproto::FileReceiver::Client receiver) {
  kj::Promise<void> prev_chunk = kj::READY_NOW;
  // TODO: see if we can easily avoid the extra round-trips while
  // still guaranteeing in-order processing (when capnp implements streams?)
  // Possibly by using UnionPromiseBuilder?
  Read(PathForHash(hash), [receiver, &prev_chunk](Chunk chunk) mutable {
    prev_chunk = prev_chunk.then([receiver, chunk]() mutable {
      auto req = receiver.sendChunkRequest();
      req.setChunk(chunk);
      return req.send().ignoreResult();
    });
  });
  return prev_chunk;
}

}  // namespace util
