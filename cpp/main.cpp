#include "manager/manager.hpp"
#include "remote/server.hpp"
#include "remote/worker.hpp"
#include "sandbox/sandbox_manager.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/version.hpp"

int main(int argc, char** argv) {
  gflags::SetUsageMessage("task-maker binary main command");
  gflags::SetVersionString(util::version);
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  if (FLAGS_daemon) util::daemonize(FLAGS_pidfile);
  if (FLAGS_mode == "manager") {
    sandbox::SandboxManager::Start();
    google::InitGoogleLogging(argv[0]);  // NOLINT
    google::InstallFailureSignalHandler();
    try {
      int ret = manager_main();
      sandbox::SandboxManager::Stop();
      return ret;
    } catch (...) {
      sandbox::SandboxManager::Stop();
    }
  }
  if (FLAGS_mode == "server") {
    google::InitGoogleLogging(argv[0]);  // NOLINT
    google::InstallFailureSignalHandler();
    return server_main();
  }
  if (FLAGS_mode == "worker") {
    sandbox::SandboxManager::Start();
    google::InitGoogleLogging(argv[0]);  // NOLINT
    google::InstallFailureSignalHandler();
    try {
      int ret = worker_main();
      sandbox::SandboxManager::Stop();
      return ret;
    } catch (...) {
      sandbox::SandboxManager::Stop();
    }
  }
  fprintf(stderr, "Invalid program mode: %s\n", FLAGS_mode.c_str());
}
