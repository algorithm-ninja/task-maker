#include "glog/logging.h"
#include "manager/manager.hpp"
#include "remote/server.hpp"
#include "remote/worker.hpp"
#include "sandbox/sandbox_manager.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/version.hpp"

int main(int argc, char** argv) {
  util::parse_flags(argc, argv);
  if (FLAGS_daemon) util::daemonize(FLAGS_pidfile);

  if (*util::manager_parser) {
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
  if (*util::server_parser) {
    google::InitGoogleLogging(argv[0]);  // NOLINT
    google::InstallFailureSignalHandler();
    return server_main();
  }
  if (*util::worker_parser) {
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
}
