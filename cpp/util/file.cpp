#include "util/file.hpp"
#include "util/flags.hpp"
#include "util/sha256.hpp"

#include <kj/async.h>
#include <kj/debug.h>
#include <kj/exception.h>
#include <kj/io.h>
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <queue>
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

namespace {

const constexpr char* kPathSeparators = "/";

bool MkDir(const std::string& dir) {
  return mkdir(dir.c_str(), S_IRWXU | S_IRWXG | S_IXOTH) != -1 ||
         errno == EEXIST;
}

bool OsRemove(const std::string& path) { return remove(path.c_str()) != -1; }

std::vector<std::string> OsListFiles(const std::string& path) {
  thread_local std::vector<std::pair<int64_t, std::string>> files;
  KJ_ASSERT(nftw(path.c_str(),
                 [](const char* fpath, const struct stat* sb, int typeflags,
                    struct FTW* ftwbuf) {
                   if (typeflags != FTW_F) return 0;
                   files.emplace_back(sb->st_atime, fpath);
                   return 0;
                 },
                 64, FTW_DEPTH | FTW_PHYS | NFTW_EXTRA_FLAGS) != -1);
  std::sort(files.begin(), files.end());
  std::vector<std::string> ret;
  ret.reserve(files.size());
  for (auto& p : files) ret.push_back(std::move(p.second));
  files.clear();
  return ret;
};

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

kj::AutoCloseFd OsTempFile(const std::string& path, std::string* tmp) {
#ifdef __APPLE__
  *tmp = path + ".";
  do {
    *tmp += 'a' + rand() % 26;
    int fd =
        open(tmp->c_str(), O_WRONLY | O_CREAT | O_CLOEXEC, S_IRUSR | S_IWUSR);
    if (fd == -1 && errno == EEXIST) continue;
    return kj::AutoCloseFd(fd);
  } while (true);
#else
  *tmp = path + ".XXXXXX";
  char data[max_path_len];
  data[0] = 0;
  strncat(data, tmp->c_str(), max_path_len - 1);  // NOLINT
  int fd = mkostemp(data, O_CLOEXEC);             // NOLINT
  *tmp = data;                                    // NOLINT
  return kj::AutoCloseFd(fd);
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
  struct stat buf {};
  if (lstat(path.c_str(), &buf) == -1) return false;
  return S_ISLNK(buf.st_mode);
}

// Returns errno, or 0 on success.
int OsAtomicCopy(const std::string& src, const std::string& dst,
                 bool overwrite = false, bool exist_ok = true) {
  if (link(src.c_str(), dst.c_str()) == -1) {
    if (errno != EEXIST) return errno;
    if (!overwrite) return errno;
    if (!exist_ok) return errno;
    if (!OsRemove(dst)) return errno;
    if (link(src.c_str(), dst.c_str()) == -1) return errno;
    return 0;
  }
  return 0;
}

util::File::ChunkProducer OsRead(const std::string& path, uint64_t limit) {
  kj::AutoCloseFd fd{open(path.c_str(), O_CLOEXEC | O_RDONLY)};  // NOLINT
  if (fd.get() == -1) {
    throw std::system_error(errno, std::system_category(), "Read " + path);
  }
  std::unique_ptr<size_t> alreadyRead = std::make_unique<size_t>(0);
  return [fd = std::move(fd), path, alreadyRead = std::move(alreadyRead), limit,
          buf = std::array<kj::byte, util::kChunkSize>()]() mutable {
    if (fd.get() == -1) return util::File::Chunk();
    ssize_t amount;
    size_t toRead = util::kChunkSize;
    if (*alreadyRead + toRead > limit) toRead = limit - *alreadyRead;
    while ((amount = read(fd, buf.data(), toRead))) {  // NOLINT
      if (amount == -1 && errno == EINTR) continue;
      if (amount == -1) break;
      *alreadyRead += amount;
      return util::File::Chunk(buf.data(), amount);
    }
    if (amount == -1) {
      fd = nullptr;
      throw std::system_error(errno, std::system_category(), "Read " + path);
    }
    return util::File::Chunk();
  };
}

util::File::ChunkReceiver OsWrite(const std::string& path, bool overwrite,
                                  bool exist_ok) {
  std::string temp_file;
  auto fd = OsTempFile(path, &temp_file);

  if (fd.get() == -1) {
    throw std::system_error(errno, std::system_category(), "Write " + path);
  }
  auto done = kj::heap<bool>();
  auto pos = kj::heap<size_t>();
  auto finalize = [done = done.get(), pos = pos.get(), temp_file]() {
    if (!*done) {
      kj::UnwindDetector detector;
      detector.catchExceptionsIfUnwinding(
          [temp_file]() { util::File::Remove(temp_file); });
      if (*pos > 0) {
        KJ_LOG(WARNING, "File never finalized!");
      }
    }
  };
  return [fd = std::move(fd), temp_file, path, overwrite, exist_ok,
          done = std::move(done), pos = std::move(pos),
          _ = kj::defer(std::move(finalize))](util::File::Chunk chunk) mutable {
    if (fd.get() == -1) return;
    if (chunk.size() == 0) {
      *done = true;
      if (fsync(fd) == -1 ||
          OsAtomicMove(temp_file, path, overwrite, exist_ok)) {
        throw std::system_error(errno, std::system_category(), "Write " + path);
      }
      fd = kj::AutoCloseFd();
      return;
    }
    *pos = 0;
    while (*pos < chunk.size()) {
      ssize_t written = write(fd, chunk.begin() + *pos,  // NOLINT
                              chunk.size() - *pos);
      if (written == -1 && errno == EINTR) continue;
      if (written == -1) {
        fd = nullptr;
        throw std::system_error(errno, std::system_category(),
                                "write " + temp_file);
      }
      *pos += written;
    }
  };
}

}  // namespace
#endif

namespace util {
std::vector<std::string> File::ListFiles(const std::string& path) {
  MakeDirs(path);
  return OsListFiles(path);
}

File::ChunkProducer File::Read(const std::string& path, uint64_t limit) {
  return OsRead(path, limit);
}
File::ChunkReceiver File::Write(const std::string& path, bool overwrite,
                                bool exist_ok) {
  MakeDirs(BaseDir(path));
  KJ_ASSERT(!(overwrite && !exist_ok));
  if (!overwrite && Size(path) >= 0) {
    if (exist_ok) return [](Chunk chunk) {};
    throw std::system_error(EEXIST, std::system_category(), "Write " + path);
  }
  return OsWrite(path, overwrite, exist_ok);
}

SHA256_t File::Hash(const std::string& path) {
  SHA256 hasher;
  auto producer = Read(path);
  Chunk chunk;
  thread_local std::vector<uint8_t> last_chunk;
  last_chunk.clear();
  size_t num_chunks = 0;
  while ((chunk = producer()).size()) {
    hasher.update(chunk.begin(), chunk.size());
    num_chunks++;
    last_chunk.assign(chunk.begin(), chunk.begin() + chunk.size());
  }
  SHA256_t hash = hasher.finalize();
  if ((num_chunks == 1 && last_chunk.size() < kInlineChunkThresh) ||
      num_chunks == 0) {
    hash.setContents(last_chunk);
  }
  return hash;
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
                    bool overwrite, bool exist_ok, bool make_dirs) {
  if (make_dirs) MakeDirs(BaseDir(to));
  auto producer = Read(from);
  auto receiver = Write(to, overwrite, exist_ok);
  Chunk chunk;
  while ((chunk = producer()).size()) {
    receiver(chunk);
  }
  receiver(chunk);
}

void File::Copy(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  MakeDirs(BaseDir(to));
  if (OsIsLink(from) || OsAtomicCopy(from, to, overwrite, exist_ok)) {
    HardCopy(from, to, overwrite, exist_ok, false);
  }
}

void File::Move(const std::string& from, const std::string& to, bool overwrite,
                bool exist_ok) {
  if (OsIsLink(from) || OsAtomicMove(from, to, overwrite, exist_ok)) {
    Copy(from, to, overwrite, exist_ok);
    Remove(from);
  }
}

void File::Remove(const std::string& path) {
  if (!OsRemove(path)) {
    throw std::system_error(errno, std::system_category(), "remove");
  }
}

void File::RemoveTree(const std::string& path) {
  if (!OsRemoveTree(path)) {
    throw std::system_error(errno, std::system_category(), "removetree");
  }
}

void File::MakeExecutable(const std::string& path) {
  if (!OsMakeExecutable(path)) {
    throw std::system_error(errno, std::system_category(), "chmod");
  }
}

void File::MakeImmutable(const std::string& path) {
  if (!OsMakeImmutable(path)) {
    throw std::system_error(errno, std::system_category(), "chmod");
  }
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
  if (path.find_last_of(kPathSeparators) == std::string::npos) return "";
  return path.substr(0, path.find_last_of(kPathSeparators));
}

std::string File::BaseName(const std::string& path) {
  return path.substr(path.find_last_of(kPathSeparators) + 1);
}

int64_t File::Size(const std::string& path) {
  struct stat st {};
  if (stat(path.c_str(), &st) != 0) {
    return -1;
  }
  return st.st_size;
}

File::ChunkReceiver File::LazyChunkReceiver(kj::Function<ChunkReceiver()> f) {
  std::unique_ptr<File::ChunkReceiver> rec(nullptr);
  return [f = std::move(f), rec = std::move(rec)](Chunk chunk) mutable {
    if (!rec) rec = std::make_unique<File::ChunkReceiver>(f());
    (*rec)(chunk);
  };
}

TempDir::TempDir(const std::string& base) {
  File::MakeDirs(base);
  path_ = OsTempDir(base);
  if (path_.empty()) {
    throw std::system_error(errno, std::system_category(), "mkdtemp");
  }
}
void TempDir::Keep() { keep_ = true; }
const std::string& TempDir::Path() const { return path_; }
TempDir::~TempDir() {  // NOLINT
  if (!keep_ && !moved_) {
    kj::UnwindDetector detector;
    detector.catchExceptionsIfUnwinding([&]() { File::RemoveTree(path_); });
  }
}

kj::Promise<void> File::Receiver::sendChunk(SendChunkContext context) {
  receiver_(context.getParams().getChunk());
  return kj::READY_NOW;
}

namespace {
struct HandleRequestFileData {
  File::ChunkProducer producer;
  capnproto::FileReceiver::Client receiver;
  static size_t num_concurrent;
  static const constexpr size_t max_concurrent = 128;
  static std::queue<kj::Own<kj::PromiseFulfiller<void>>> waiting;
};

size_t HandleRequestFileData::num_concurrent = 0;
std::queue<kj::Own<kj::PromiseFulfiller<void>>> HandleRequestFileData::waiting;

kj::Promise<void> next_chunk(HandleRequestFileData data) {
  File::Chunk chunk = data.producer();
  auto req = data.receiver.sendChunkRequest();
  req.setChunk(chunk);
  return req.send().ignoreResult().then(
      [sz = chunk.size(),
       data = std::move(data)]() mutable -> kj::Promise<void> {
        if (sz) return next_chunk(std::move(data));
        if (!HandleRequestFileData::waiting.empty()) {
          HandleRequestFileData::waiting.front()->fulfill();
          HandleRequestFileData::waiting.pop();
        }
        HandleRequestFileData::num_concurrent--;
        return kj::READY_NOW;
      });
}
}  // namespace

kj::Promise<void> File::HandleRequestFile(
    FileWrapper* wrapper, capnproto::FileReceiver::Client receiver,
    uint64_t amount) {
  // TODO: see if we can easily avoid the extra round-trips while
  // still guaranteeing in-order processing (when capnp implements streams?)
  // Possibly by using UnionPromiseBuilder?
  if (HandleRequestFileData::num_concurrent <
      HandleRequestFileData::max_concurrent) {
    HandleRequestFileData::num_concurrent++;
    HandleRequestFileData data{wrapper->Read(amount), receiver};
    return next_chunk(std::move(data));
  }
  auto pf = kj::newPromiseAndFulfiller<void>();
  HandleRequestFileData::waiting.push(std::move(pf.fulfiller));
  return pf.promise.then([wrapper = wrapper, receiver, amount]() mutable {
    return File::HandleRequestFile(wrapper, receiver, amount);
  });
}

kj::Promise<void> File::HandleRequestFile(
    const util::SHA256_t& hash, capnproto::FileReceiver::Client receiver,
    uint64_t amount) {
  if (hash.hasContents()) {
    auto req = receiver.sendChunkRequest();
    kj::ArrayPtr<const uint8_t> chunk = hash.getContents();
    if (chunk.size() > amount) chunk = {chunk.begin(), amount};
    req.setChunk(chunk);
    return req.send().ignoreResult().then([receiver]() mutable {
      return receiver.sendChunkRequest().send().ignoreResult();
    });
  }
  util::FileWrapper wrapper = FileWrapper::FromPath(PathForHash(hash));
  return HandleRequestFile(&wrapper, receiver, amount);
}

FileWrapper FileWrapper::FromPath(std::string path) {
  FileWrapper file;
  file.type_ = FileWrapper::FileWrapperType::PATH;
  file.path_ = std::move(path);
  return file;
}

FileWrapper FileWrapper::FromContent(std::string content) {
  FileWrapper file;
  file.type_ = FileWrapper::FileWrapperType::CONTENT;
  file.content_ = std::move(content);
  return file;
}

File::ChunkProducer FileWrapper::Read(uint64_t limit) {
  if (type_ == FileWrapper::FileWrapperType::PATH) {
    return File::Read(path_, limit);
  }

  std::unique_ptr<size_t> pos = std::make_unique<size_t>(0);
  return [this, pos = std::move(pos), limit]() mutable {
    if (*pos < content_.size() && *pos < limit) {
      auto end = content_.begin() + *pos + util::kChunkSize;
      if (end > content_.end()) end = content_.end();
      if (static_cast<size_t>(end - content_.begin()) > limit) {
        end = content_.begin() + limit;
      }
      size_t amount = end - content_.begin() - *pos;
      auto chunk = util::File::Chunk(
          // NOLINTNEXTLINE
          reinterpret_cast<const kj::byte*>(&content_[0] + *pos), amount);
      *pos += amount;
      return chunk;
    }
    return util::File::Chunk();
  };
}

}  // namespace util
