#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "sandbox/sandbox.hpp"

#include <memory>

namespace {

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
  options.args.push_back("15");
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
  options.args.push_back("6");
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
  options.args.push_back("0.1");
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.wall_time_millis, 70);
  EXPECT_LE(info.wall_time_millis, 130);
  EXPECT_LE(info.cpu_time_millis, 30);
  EXPECT_LE(info.sys_time_millis, 30);
}

TEST(UnixTest, TestBusyWaitArg1) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "busywait_arg1");
  options.args.push_back("0.1");
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.cpu_time_millis + info.sys_time_millis, 70);
  EXPECT_LE(info.cpu_time_millis + info.sys_time_millis, 130);
  EXPECT_GE(info.wall_time_millis, 70);
  EXPECT_LE(info.wall_time_millis, 130);
  EXPECT_LE(info.sys_time_millis, 30);
}

TEST(UnixTest, TestMallocArg1) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "malloc_arg1");
  options.args.push_back("10");
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.memory_usage_kb, 10 * sizeof(int) * 1024);
  EXPECT_LE(info.memory_usage_kb, 12 * sizeof(int) * 1024);
}

TEST(UnixTest, TestMemoryLimitOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "malloc_arg1");
  options.args.push_back("10");
  options.memory_limit_kb = 20 * sizeof(int) * 1024;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.memory_usage_kb, 10 * sizeof(int) * 1024);
  EXPECT_LE(info.memory_usage_kb, 12 * sizeof(int) * 1024);
}

TEST(UnixTest, TestMemoryLimitNotOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "malloc_arg1");
  options.args.push_back("10");
  options.memory_limit_kb = 10 * sizeof(int) * 1024;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 11);
  EXPECT_EQ(info.status_code, 0);
}

TEST(UnixTest, TestWallLimitOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "wait_arg1");
  options.args.push_back("0.1");
  options.wall_limit_millis = 200;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.wall_time_millis, 90);
  EXPECT_LE(info.wall_time_millis, 130);
}

TEST(UnixTest, TestWallLimitNotOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "wait_arg1");
  options.args.push_back("1");
  options.wall_limit_millis = 100;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 9);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.wall_time_millis, 100);
  EXPECT_LE(info.wall_time_millis, 130);
}

TEST(UnixTest, TestCpuLimitOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "busywait_arg1");
  options.args.push_back("0.1");
  options.cpu_limit_millis = 1000;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 0);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.cpu_time_millis + info.sys_time_millis, 90);
  EXPECT_LE(info.cpu_time_millis + info.sys_time_millis, 130);
}

TEST(UnixTest, TestCpuLimitNotOk) {
  std::unique_ptr<Sandbox> sandbox = Sandbox::Create();
  ASSERT_TRUE(sandbox);
  ExecutionOptions options("sandbox/test", "busywait_arg1");
  options.args.push_back("10");
  options.cpu_limit_millis = 1000;
  ExecutionInfo info;
  std::string error_msg;
  EXPECT_TRUE(sandbox->Execute(options, &info, &error_msg));
  EXPECT_EQ(error_msg, "");
  EXPECT_EQ(info.signal, 9);
  EXPECT_EQ(info.status_code, 0);
  EXPECT_GE(info.cpu_time_millis + info.sys_time_millis, 990);
  EXPECT_LE(info.cpu_time_millis + info.sys_time_millis, 1030);
}

}  // namespace
