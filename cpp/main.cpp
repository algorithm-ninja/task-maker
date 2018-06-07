#include "manager/manager.hpp"
#include "plog/Appenders/ColorConsoleAppender.h"
#include "plog/Formatters/TxtFormatter.h"
#include "plog/Init.h"
#include "plog/Log.h"
#include "remote/server.hpp"
#include "remote/worker.hpp"
#include "sandbox/sandbox_manager.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/version.hpp"

int main(int argc, char** argv) {
  util::parse_flags(argc, argv);
  if (FLAGS_daemon) util::daemonize(FLAGS_pidfile);

  plog::ColorConsoleAppender<plog::TxtFormatter> appender;

  plog::Severity severity;
  if (FLAGS_verbose == 0)
    severity = plog::info;
  else if (FLAGS_verbose == 1)
    severity = plog::debug;
  else
    severity = plog::verbose;

  plog::init(severity, &appender);

  if (*util::manager_parser) {
    sandbox::SandboxManager::Start();
    try {
      int ret = manager_main();
      sandbox::SandboxManager::Stop();
      return ret;
    } catch (...) {
      sandbox::SandboxManager::Stop();
    }
  }
  if (*util::server_parser) {
    return server_main();
  }
  if (*util::worker_parser) {
    sandbox::SandboxManager::Start();
    try {
      int ret = worker_main();
      sandbox::SandboxManager::Stop();
      return ret;
    } catch (...) {
      sandbox::SandboxManager::Stop();
    }
  }
}
