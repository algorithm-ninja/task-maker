#include "util/which.hpp"
#include <cstdlib>
#include <fstream>
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "util/file.hpp"

namespace {

const std::string test_tmpdir = "/tmp/task_maker_testdir";

void createFile(const std::string& path) { std::ofstream os(path); }

// NOLINTNEXTLINE
TEST(Which, Which) {
  util::TempDir tmpdir1(test_tmpdir + "/which");
  util::TempDir tmpdir2(test_tmpdir + "/which");
  createFile(tmpdir1.Path() + "/cmd");
  createFile(tmpdir2.Path() + "/cmd");
  createFile(tmpdir2.Path() + "/cmd2");
  std::string path = tmpdir1.Path() + ":" + tmpdir2.Path();
  setenv("PATH", path.c_str(), 1);

  EXPECT_EQ(util::which("cmd"), tmpdir1.Path() + "/cmd");
  EXPECT_EQ(util::which("cmd2"), tmpdir2.Path() + "/cmd2");
}

// NOLINTNEXTLINE
TEST(Which, WhichEmptyPath) {
  unsetenv("PATH");
  EXPECT_THROW(util::which("cmd"), std::exception);  // NOLINT
}

// NOLINTNEXTLINE
TEST(Which, WhichUsesCache) {
  std::string path;
  {
    util::TempDir tmpdir1(test_tmpdir + "/which");
    createFile(tmpdir1.Path() + "/cmd");
    setenv("PATH", tmpdir1.Path().c_str(), 1);
    path = util::which("cmd");
    EXPECT_EQ(path, tmpdir1.Path() + "/cmd");
  }
  EXPECT_EQ(util::which("cmd"), path);
}

// NOLINTNEXTLINE
TEST(Which, WhichCacheDisabled) {
  std::string path;
  {
    util::TempDir tmpdir1(test_tmpdir + "/which");
    createFile(tmpdir1.Path() + "/cmd");
    setenv("PATH", tmpdir1.Path().c_str(), 1);
    path = util::which("cmd");
    EXPECT_EQ(path, tmpdir1.Path() + "/cmd");
  }
  EXPECT_EQ(util::which("cmd", false), "");
}

}  // namespace
