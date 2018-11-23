#include "util/file.hpp"
#include <dirent.h>
#include <fcntl.h>
#include <ftw.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <cstdio>
#include <fstream>
#include <vector>
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "util/flags.hpp"
#include "util/sha256.hpp"

namespace {

using ::testing::EndsWith;
using ::testing::IsEmpty;
using ::testing::StartsWith;
using ::testing::UnorderedElementsAreArray;

const std::string test_tmpdir = "/tmp/task_maker_testdir";

int unlink_cb(const char* fpath, const struct stat* /*unused*/, int /*unused*/,
              struct FTW* /*unused*/) {
  int rv = remove(fpath);
  if (rv) perror(fpath);
  return rv;
}

int rmrf(const char* path) {
  return nftw(path, unlink_cb, 64, FTW_DEPTH | FTW_PHYS);
}

void writeFile(const std::string& path, const std::string& content) {
  std::ofstream of(path);
  of << content;
}

void writeFile(util::File::ChunkReceiver* receiver,
               const std::string& content) {
  auto data = reinterpret_cast<const kj::byte*>(content.data());  // NOLINT
  size_t written = 0;
  while (written < content.size()) {
    size_t size = std::min(content.size() - written,
                           static_cast<size_t>(util::kChunkSize));
    util::File::Chunk chunk(data + written, size);
    (*receiver)(chunk);
    written += size;
  }
  (*receiver)(util::File::Chunk());
}

std::string readFile(const std::string& path) {
  std::ifstream t(path);
  std::string str((std::istreambuf_iterator<char>(t)),
                  std::istreambuf_iterator<char>());
  return str;
}

std::string readFile(util::File::ChunkProducer* producer) {
  util::File::Chunk chunk;
  std::string content;
  while ((chunk = (*producer)()).size()) {
    content += std::string(chunk.asChars().begin(), chunk.size());
  }
  return content;
}

bool fileExists(const std::string& path) {
  auto file = open(path.c_str(), O_RDONLY | O_CLOEXEC);
  if (file < 0) return false;
  close(file);
  return true;
}

bool dirExists(const std::string& path) {
  auto dir = opendir(path.c_str());
  if (!dir) return false;
  closedir(dir);
  return true;
}

std::string makeTestDir(const std::string& name) {
  mkdir(test_tmpdir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
  std::string testdir = test_tmpdir + "/" + name;
  rmrf(testdir.c_str());
  mkdir(testdir.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
  return testdir;
}

/*
 * ListFiles
 */

// NOLINTNEXTLINE
TEST(File, ListFiles) {
  std::string testdir = makeTestDir("list_files");
  std::vector<std::string> files;
  for (auto name : {"file42", "file12", "file68"}) {
    files.push_back(testdir + "/" + name);
  }

  for (const auto& file : files) {
    writeFile(file, "fooo");
  }
  chdir("/");
  auto foundFiles = util::File::ListFiles(testdir);
  EXPECT_THAT(files, UnorderedElementsAreArray(foundFiles));
}

// NOLINTNEXTLINE
TEST(File, ListFilesEmpty) {
  std::string testdir = makeTestDir("list_files");
  chdir("/");
  auto foundFiles = util::File::ListFiles(testdir);
  EXPECT_THAT(foundFiles, IsEmpty());
}

// NOLINTNEXTLINE
TEST(File, ListFilesNoSuchDir) {
  std::string testdir = test_tmpdir + "/lolnope/ahah";
  chdir("/");
  auto foundFiles = util::File::ListFiles(testdir);
  EXPECT_THAT(foundFiles, IsEmpty());
}

/*
 * Read
 */

// NOLINTNEXTLINE
TEST(File, Read) {
  std::string testdir = makeTestDir("read");
  std::string filepath = testdir + "/file";
  std::string content = "lallabalalla\n";
  writeFile(filepath, content);
  auto reader = util::File::Read(filepath);
  std::string realContent = readFile(&reader);
  EXPECT_EQ(content, realContent);
}

// NOLINTNEXTLINE
TEST(File, ReadBigFile) {
  std::string testdir = makeTestDir("read");
  std::string filepath = testdir + "/bigfile";
  std::string content(util::kChunkSize * 2 + 1, 'x');

  writeFile(filepath, content);
  auto reader = util::File::Read(filepath);
  std::string realContent = readFile(&reader);
  EXPECT_EQ(content, realContent);
}

// NOLINTNEXTLINE
TEST(File, ReadNoSuchFile) {
  std::string filepath = "/no/such/file";
  EXPECT_THROW(util::File::Read(filepath), std::system_error);  // NOLINT
}

/*
 * Write
 */

// NOLINTNEXTLINE
TEST(File, Write) {
  std::string testdir = makeTestDir("write");
  std::string filepath = testdir + "/file";
  std::string content = "wowowow\n";
  {
    auto writer = util::File::Write(filepath);
    writeFile(&writer, content);
  }
  ASSERT_EQ(content, readFile(filepath));
}

// NOLINTNEXTLINE
TEST(File, WriteBigFile) {
  std::string testdir = makeTestDir("write");
  std::string filepath = testdir + "/bigfile";
  std::string content(util::kChunkSize * 2 + 1, 'x');
  {
    auto writer = util::File::Write(filepath);
    writeFile(&writer, content);
  }
  ASSERT_EQ(content, readFile(filepath));
}

// NOLINTNEXTLINE
TEST(File, WriteNotOverwrite) {
  std::string testdir = makeTestDir("write");
  std::string filepath = testdir + "/file";
  std::string content{"alsdasdl"};
  writeFile(filepath, content);
  {
    auto writer = util::File::Write(filepath, false);
    writeFile(&writer, "this should not be written");
  }
  ASSERT_EQ(content, readFile(filepath));
}

// NOLINTNEXTLINE
TEST(File, WriteOverwrite) {
  std::string testdir = makeTestDir("write");
  std::string filepath = testdir + "/file";
  std::string content{"alsdasdl"};
  writeFile(filepath, "this should not be here");
  {
    auto writer = util::File::Write(filepath, true);
    writeFile(&writer, content);
  }
  ASSERT_EQ(content, readFile(filepath));
}

// NOLINTNEXTLINE
TEST(File, WriteExistsNotOk) {
  std::string testdir = makeTestDir("write");
  std::string filepath = testdir + "/file";
  std::string content{"this should stay here"};
  writeFile(filepath, content);
  EXPECT_THROW(util::File::Write(filepath, false, false),  // NOLINT
               std::system_error);
  ASSERT_EQ(content, readFile(filepath));
}

/*
 * Hash
 */

// NOLINTNEXTLINE
TEST(File, Hash) {
  std::string testdir = makeTestDir("hash");
  std::string filepath = testdir + "/file";
  std::string content{"random content"};
  writeFile(filepath, content);
  util::SHA256_t hash = util::File::Hash(filepath);
  EXPECT_EQ(hash.Hex(),
            "276e3a2aee034b91dba3e553be3a560d27b380575fd43475fdc8f46d552709bb");
  EXPECT_FALSE(hash.isZero());
  EXPECT_TRUE(hash.hasContents());
  EXPECT_EQ(content, std::string(hash.getContents().asChars().begin(),
                                 hash.getContents().size()));
}

// NOLINTNEXTLINE
TEST(File, HashBigFile) {
  std::string testdir = makeTestDir("hash");
  std::string filepath = testdir + "/bigfile";
  std::string content(util::kChunkSize * 2 + 1, 'x');
  writeFile(filepath, content);
  util::SHA256_t hash = util::File::Hash(filepath);
  EXPECT_EQ(hash.Hex(),
            "71ac24a75f6bc57bc51b43b3d13c3009aa243986b77a92102a3097c9e53123e9");
  EXPECT_FALSE(hash.isZero());
  EXPECT_FALSE(hash.hasContents());
}

// NOLINTNEXTLINE
TEST(File, HashEmptyFile) {
  std::string testdir = makeTestDir("hash");
  std::string filepath = testdir + "/file";
  std::string content;
  writeFile(filepath, content);
  util::SHA256_t hash = util::File::Hash(filepath);
  EXPECT_EQ(hash.Hex(),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
}

// NOLINTNEXTLINE
TEST(File, HashNoSuchFile) {
  std::string testdir = makeTestDir("hash");
  std::string filepath = testdir + "/no/such/file";
  EXPECT_THROW(util::File::Hash(filepath), std::system_error);  // NOLINT
}

/*
 * MakeDirs
 */

// NOLINTNEXTLINE
TEST(File, MakeDirs) {
  std::string testdir = makeTestDir("makeDirs");
  std::string dirpath = testdir + "/wow/such/dir";
  EXPECT_FALSE(dirExists(dirpath));
  util::File::MakeDirs(dirpath);
  EXPECT_TRUE(dirExists(dirpath));
}

// NOLINTNEXTLINE
TEST(File, MakeDirsCannot) {
  std::string testdir = makeTestDir("makeDirs");
  std::string dirpath1 = testdir + "/nope";
  mkdir(dirpath1.c_str(), 0);
  std::string dirpath = dirpath1 + "/wow/such/dir";
  EXPECT_THROW(util::File::MakeDirs(dirpath), std::system_error);  // NOLINT
}

/*
 * Copy
 */

// NOLINTNEXTLINE
TEST(File, Copy) {
  std::string testdir = makeTestDir("copy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, content);
  util::File::Copy(filepath, filepath2);
  EXPECT_TRUE(fileExists(filepath));
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, CopyNoOverwrite) {
  std::string testdir = makeTestDir("copy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, "This should not be copied");
  writeFile(filepath2, content);
  util::File::Copy(filepath, filepath2, false);
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, CopyOverwrite) {
  std::string testdir = makeTestDir("copy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, content);
  writeFile(filepath2, "This should be overwritten");
  util::File::Copy(filepath, filepath2, true);
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, CopyExistNotOk) {
  std::string testdir = makeTestDir("copy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, "This should not be copied");
  writeFile(filepath2, content);
  EXPECT_THROW(util::File::Copy(filepath, filepath2, false, false),  // NOLINT
               std::system_error);
}

/*
 * HardCopy
 */

// NOLINTNEXTLINE
TEST(File, HardCopy) {
  std::string testdir = makeTestDir("hardcopy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, content);
  util::File::HardCopy(filepath, filepath2);
  EXPECT_TRUE(fileExists(filepath));
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, HardCopyNoOverwrite) {
  std::string testdir = makeTestDir("hardcopy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, "This should not be copied");
  writeFile(filepath2, content);
  util::File::HardCopy(filepath, filepath2, false);
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, HardCopyOverwrite) {
  std::string testdir = makeTestDir("hardcopy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, content);
  writeFile(filepath2, "This should be overwritten");
  util::File::HardCopy(filepath, filepath2, true);
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, HardCopyExistNotOk) {
  std::string testdir = makeTestDir("hardcopy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, "This should not be copied");
  writeFile(filepath2, content);
  EXPECT_THROW(  // NOLINT
      util::File::HardCopy(filepath, filepath2, false, false),
      std::system_error);
}

// NOLINTNEXTLINE
TEST(File, HardCopyMakeDirs) {
  std::string testdir = makeTestDir("hardcopy");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/newdir/file2";
  std::string content{"This should be copied"};
  writeFile(filepath, content);
  util::File::HardCopy(filepath, filepath2, true, true, true);
  EXPECT_EQ(content, readFile(filepath2));
}

/*
 * Move
 */

// NOLINTNEXTLINE
TEST(File, Move) {
  std::string testdir = makeTestDir("move");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, content);
  util::File::Move(filepath, filepath2);
  EXPECT_FALSE(fileExists(filepath));
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, MoveNoOverwrite) {
  std::string testdir = makeTestDir("move");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, "This should not be copied");
  writeFile(filepath2, content);
  util::File::Move(filepath, filepath2, false);
  EXPECT_TRUE(fileExists(filepath));
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, MoveOverwrite) {
  std::string testdir = makeTestDir("move");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, content);
  writeFile(filepath2, "This should be overwritten");
  util::File::Move(filepath, filepath2, true);
  EXPECT_FALSE(fileExists(filepath));
  EXPECT_EQ(content, readFile(filepath2));
}

// NOLINTNEXTLINE
TEST(File, MoveExistNotOk) {
  std::string testdir = makeTestDir("move");
  std::string filepath = testdir + "/file";
  std::string filepath2 = testdir + "/file2";
  std::string content{"hollaaa"};
  writeFile(filepath, "This should not be copied");
  writeFile(filepath2, content);
  EXPECT_THROW(util::File::Move(filepath, filepath2, false, false),  // NOLINT
               std::system_error);
}

/*
 * Remove
 */

// NOLINTNEXTLINE
TEST(File, Remove) {
  std::string testdir = makeTestDir("remove");
  std::string filepath = testdir + "/file";
  writeFile(filepath, "holaa");
  util::File::Remove(filepath);
  EXPECT_FALSE(fileExists(filepath));
}

// NOLINTNEXTLINE
TEST(File, RemoveNoSuchFile) {
  std::string testdir = makeTestDir("remove");
  std::string filepath = testdir + "/file";
  EXPECT_THROW(util::File::Remove(filepath), std::system_error);  // NOLINT
}

/*
 * RemoveTree
 */

// NOLINTNEXTLINE
TEST(File, RemoveTree) {
  std::string testdir = makeTestDir("removetree");
  std::string dirpath = testdir + "/dir";
  std::string dirpath2 = dirpath + "/baz";
  mkdir(dirpath.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
  mkdir(dirpath2.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
  std::array<std::string, 3> files = {dirpath + "/foo", dirpath + "/bar",
                                      dirpath2 + "/buz"};
  for (const auto& file : files) writeFile(file, "holaa");
  util::File::RemoveTree(dirpath);
  for (const auto& file : files) EXPECT_FALSE(fileExists(file));
  EXPECT_FALSE(dirExists(dirpath));
  EXPECT_FALSE(dirExists(dirpath2));
}

// NOLINTNEXTLINE
TEST(File, RemoveTreeNoSuchFile) {
  std::string testdir = makeTestDir("removetree");
  std::string dirpath = testdir + "/nope/noo";
  EXPECT_THROW(util::File::RemoveTree(dirpath), std::system_error);  // NOLINT
}

/*
 * MakeExecutable
 */

// NOLINTNEXTLINE
TEST(File, MakeExecutable) {
  std::string testdir = makeTestDir("markexecutable");
  std::string filepath = testdir + "/file";
  writeFile(filepath, "foo");
  util::File::MakeExecutable(filepath);
  struct stat fileStat {};
  EXPECT_NE(stat(filepath.c_str(), &fileStat), -1);
  EXPECT_NE(fileStat.st_mode & S_IRUSR, 0);
  EXPECT_NE(fileStat.st_mode & S_IXUSR, 0);
}

// NOLINTNEXTLINE
TEST(File, MakeExecutableNoSuchFile) {
  std::string testdir = makeTestDir("markexecutable");
  std::string filepath = testdir + "/lol/nope";
  EXPECT_THROW(util::File::MakeExecutable(filepath),  // NOLINT
               std::system_error);
}

/*
 * MakeImmutable
 */

// NOLINTNEXTLINE
TEST(File, MakeImmutable) {
  std::string testdir = makeTestDir("markimmutable");
  std::string filepath = testdir + "/file";
  writeFile(filepath, "foo");
  util::File::MakeImmutable(filepath);
  struct stat fileStat {};
  EXPECT_NE(stat(filepath.c_str(), &fileStat), -1);
  EXPECT_NE(fileStat.st_mode & S_IRUSR, 0);
}

// NOLINTNEXTLINE
TEST(File, MakeImmutableNoSuchFile) {
  std::string testdir = makeTestDir("markimmutable");
  std::string filepath = testdir + "/lol/nope";
  EXPECT_THROW(util::File::MakeImmutable(filepath),  // NOLINT
               std::system_error);
}

/*
 * PathForHash
 */

// NOLINTNEXTLINE
TEST(File, PathForHash) {
  Flags::store_directory = "/path";
  auto hash = util::File::Hash("/dev/null");
  auto hex = hash.Hex();
  auto path = util::File::PathForHash(hash);
  EXPECT_THAT(path, StartsWith(Flags::store_directory));
  EXPECT_THAT(path, EndsWith(hex));
}

/*
 * JoinPath
 */

// NOLINTNEXTLINE
TEST(File, JoinPath) {
  EXPECT_EQ(util::File::JoinPath("a/b", "c/d"), "a/b/c/d");
}

// NOLINTNEXTLINE
TEST(File, JoinPathFirstAbs) {
  EXPECT_EQ(util::File::JoinPath("/a/b", "c/d"), "/a/b/c/d");
}

// NOLINTNEXTLINE
TEST(File, JoinPathSecondAbs) {
  EXPECT_EQ(util::File::JoinPath("/a/b", "/c/d"), "/c/d");
}

/*
 * BaseDir
 */

// NOLINTNEXTLINE
TEST(File, BaseDir) { EXPECT_EQ(util::File::BaseDir("a/b/c"), "a/b"); }

// NOLINTNEXTLINE
TEST(File, BaseDirSingleFile) { EXPECT_EQ(util::File::BaseDir("a"), ""); }

/*
 * BaseName
 */

// NOLINTNEXTLINE
TEST(File, BaseName) { EXPECT_EQ(util::File::BaseName("a/b/c"), "c"); }

// NOLINTNEXTLINE
TEST(File, BaseNameSingleFile) { EXPECT_EQ(util::File::BaseName("a"), "a"); }

/*
 * Size
 */

// NOLINTNEXTLINE
TEST(File, Size) {
  std::string testdir = makeTestDir("size");
  std::string filepath = testdir + "/file";
  std::string content = "foobar";
  writeFile(filepath, content);
  EXPECT_EQ(util::File::Size(filepath), content.size());
}

// NOLINTNEXTLINE
TEST(File, SizeEmpty) {
  std::string testdir = makeTestDir("size");
  std::string filepath = testdir + "/file";
  std::string content;
  writeFile(filepath, content);
  EXPECT_EQ(util::File::Size(filepath), content.size());
}

// NOLINTNEXTLINE
TEST(File, SizeNoSuchFile) {
  std::string testdir = makeTestDir("size");
  std::string filepath = testdir + "/nope/nono";
  EXPECT_LT(util::File::Size(filepath), 0);
}

/*
 * Exists
 */

// NOLINTNEXTLINE
TEST(File, Exists) {
  std::string testdir = makeTestDir("size");
  std::string filepath = testdir + "/file";
  writeFile(filepath, "foobar");
  EXPECT_TRUE(util::File::Exists(filepath));
}

// NOLINTNEXTLINE
TEST(File, ExistsNoSuchFile) {
  std::string testdir = makeTestDir("size");
  std::string filepath = testdir + "/nope";
  EXPECT_FALSE(util::File::Exists(filepath));
}

/*
 * TempDir
 */

// NOLINTNEXTLINE
TEST(TempDir, TempDir) {
  std::string testdir = makeTestDir("tempdir");
  std::string tempdirPath;
  {
    util::TempDir tempdir(testdir);
    tempdirPath = tempdir.Path();
    EXPECT_TRUE(dirExists(tempdirPath));
    EXPECT_THAT(tempdir.Path(), StartsWith(testdir));
  }
  EXPECT_FALSE(dirExists(tempdirPath));
}

// NOLINTNEXTLINE
TEST(TempDir, TempDirKeep) {
  std::string testdir = makeTestDir("tempdir");
  std::string tempdirPath;
  {
    util::TempDir tempdir(testdir);
    tempdir.Keep();
    tempdirPath = tempdir.Path();
    EXPECT_TRUE(dirExists(tempdirPath));
    EXPECT_THAT(tempdir.Path(), StartsWith(testdir));
  }
  EXPECT_TRUE(dirExists(tempdirPath));
}

// NOLINTNEXTLINE
TEST(TempDir, TempDirMove) {
  std::string testdir = makeTestDir("tempdir");
  std::string tempdirPath;
  {
    util::TempDir tempdir(testdir);
    tempdirPath = tempdir.Path();
    EXPECT_TRUE(dirExists(tempdirPath));
    {
      util::TempDir other = std::move(tempdir);
      EXPECT_TRUE(dirExists(tempdirPath));
    }
    EXPECT_FALSE(dirExists(tempdirPath));
  }
}

}  // namespace
