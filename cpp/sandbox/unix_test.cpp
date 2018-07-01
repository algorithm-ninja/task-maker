#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <cstdlib>
#include <memory>
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "sandbox/sandbox.hpp"

namespace {

const std::string TEST_TMPDIR = "/tmp/task_maker_testdir";

using ::testing::AnyOf;
using ::testing::Eq;
using ::testing::StartsWith;

using namespace sandbox;

TEST(UnixTest, TestNoDir) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("foo", "bar");
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_FALSE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_THAT(error_msg, StartsWith("chdir:"));
}

TEST(UnixTest, TestNoFile) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "foo");
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_FALSE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_THAT(error_msg, StartsWith("exec:"));
}

TEST(UnixTest, TestReturnArg1) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "return_arg1");
  options.SetArgs({"15"});
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.status_code, 15);
  EXPECT_EQ(info.signal, 0);
}

TEST(UnixTest, TestSignalArg1) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "signal_arg1");
  options.SetArgs({"6"});
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 6);
  EXPECT_EQ(info.status_code, 0);
}

TEST(UnixTest, TestWaitArg1) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "wait_arg1");
  options.SetArgs({"1"});
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.wall_time_millis, 900);
  EXPECT_LE(info.wall_time_millis, 2000);
  EXPECT_LE(info.cpu_time_millis, 300);
  EXPECT_LE(info.sys_time_millis, 300);
}

TEST(UnixTest, TestBusyWaitArg1) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "busywait_arg1");
  options.SetArgs({"1"});
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.cpu_time_millis + info.sys_time_millis, 900);
  EXPECT_LE(info.cpu_time_millis + info.sys_time_millis, 1500);
  EXPECT_GE(info.wall_time_millis, 900);
  EXPECT_LE(info.wall_time_millis, 2000);
  EXPECT_LE(info.sys_time_millis, 500);
}

TEST(UnixTest, TestMallocArg1) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "malloc_arg1");
  options.SetArgs({"10"});
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.memory_usage_kb, 10 * sizeof(int) * 1024);
  EXPECT_LE(info.memory_usage_kb, 15 * sizeof(int) * 1024);
}

TEST(UnixTest, TestMemoryLimitOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "malloc_arg1");
  options.SetArgs({"10"});
  options.memory_limit_kb = 20 * sizeof(int) * 1024;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.memory_usage_kb, 10 * sizeof(int) * 1024);
  EXPECT_LE(info.memory_usage_kb, 15 * sizeof(int) * 1024);
}

TEST(UnixTest, TestMemoryLimitNotOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "malloc_arg1");
  options.SetArgs({"10"});
  options.memory_limit_kb = 10 * sizeof(int) * 1024;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_TRUE(info.signal == SIGSEGV || info.signal == SIGKILL);
  EXPECT_EQ(info.status_code, 0);
}

TEST(UnixTest, TestWallLimitOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "wait_arg1");
  options.SetArgs({"1"});
  options.wall_limit_millis = 2000;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.wall_time_millis, 900);
  EXPECT_LE(info.wall_time_millis, 1900);
}

TEST(UnixTest, TestWallLimitNotOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "wait_arg1");
  options.SetArgs({"1"});
  options.wall_limit_millis = 200;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, SIGKILL);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.wall_time_millis, 100);
  EXPECT_LE(info.wall_time_millis, 800);
}

TEST(UnixTest, TestCpuLimitOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "busywait_arg1");
  options.SetArgs({"1"});
  options.cpu_limit_millis = 2000;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.cpu_time_millis + info.sys_time_millis, 900);
  EXPECT_LE(info.cpu_time_millis + info.sys_time_millis, 1500);
}

TEST(UnixTest, TestCpuLimitNotOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "busywait_arg1");
  options.SetArgs({"10"});
  options.cpu_limit_millis = 1000;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_THAT(info.signal, AnyOf(Eq(SIGKILL), Eq(SIGXCPU)));
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.cpu_time_millis + info.sys_time_millis, 900);
  EXPECT_LE(info.cpu_time_millis + info.sys_time_millis, 1500);
}

TEST(UnixTest, TestIORedirect) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "copy_int");
  const char* test_tmpdir = TEST_TMPDIR.c_str();
  mkdir(test_tmpdir, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
  strcpy(options.stdin_file, test_tmpdir);
  strcat(options.stdin_file, "/in");

  strcpy(options.stdout_file, test_tmpdir);
  strcat(options.stdout_file, "/out");

  strcpy(options.stderr_file, test_tmpdir);
  strcat(options.stderr_file, "/err");

  {
    FILE* in = fopen(options.stdin_file, "w");
    EXPECT_TRUE(in);
    EXPECT_EQ(fprintf(in, "10"), 2);
    EXPECT_EQ(fclose(in), 0);
  }

  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);

  int out = 0;
  int err = 0;

  {
    FILE* fout = fopen(options.stdout_file, "r");
    FILE* ferr = fopen(options.stderr_file, "r");
    EXPECT_TRUE(fout);
    EXPECT_TRUE(ferr);
    EXPECT_EQ(fscanf(fout, "%d", &out), 1);
    EXPECT_EQ(fscanf(ferr, "%d", &err), 1);
    EXPECT_EQ(fclose(fout), 0);
    EXPECT_EQ(fclose(ferr), 0);
  }

  EXPECT_EQ(out, 10);
  EXPECT_EQ(err, 20);
}

}  // namespace
