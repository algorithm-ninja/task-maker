#include "worker/main.hpp"
#include <capnp/ez-rpc.h>
#include <thread>

#include "capnp/server.capnp.h"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/log_manager.hpp"
#include "util/misc.hpp"
#include "util/version.hpp"
#include "worker/executor.hpp"
#include "worker/manager.hpp"

const size_t EXP_BACKOFF_MIN = 1;
const size_t EXP_BACKOFF_MAX = 60000;
const size_t EXP_BACKOFF_MAX_RETRIES = 70;

namespace worker {
kj::MainBuilder::Validity Main::Run() {
  if (Flags::daemon) {
    util::daemonize("worker", Flags::pidfile);
  }
  if (Flags::server == "") {
    return "You need to specify a server!";
  }
  if (!Flags::num_cores) {
    Flags::num_cores = std::thread::hardware_concurrency();
  }
  util::LogManager log_manager(context);
  size_t sleepTime = 0;
  size_t numRetries = 0;
  while (true) {
    try {
      Manager manager(Flags::server, Flags::port, Flags::num_cores,
                      Flags::pending_requests, Flags::name);
      manager.Run();
      return true;
    } catch (std::exception& ex) {
      KJ_LOG(ERROR, "Manager failed!", ex.what());
      bool connectionRefused =
          strstr(ex.what(), "connect(): Connection refused");

      if (connectionRefused) {
        numRetries++;
        sleepTime *= 2;
        if (sleepTime < EXP_BACKOFF_MIN) sleepTime = EXP_BACKOFF_MIN;
        if (sleepTime > EXP_BACKOFF_MAX) sleepTime = EXP_BACKOFF_MAX;
        if (numRetries > EXP_BACKOFF_MAX_RETRIES) return false;
      } else {
        numRetries = 0;
        sleepTime = EXP_BACKOFF_MIN;
      }
      KJ_LOG(INFO, "Sleeping for", sleepTime, "ms");
      std::this_thread::sleep_for(std::chrono::milliseconds(sleepTime));
    }
  }
}

kj::MainFunc Main::getMain() {
  return kj::MainBuilder(context, "Task-Maker Worker (" + util::version + ")",
                         "Executes requests pulled from a server")
      .addOptionWithArg({'L', "logfile"}, util::setString(Flags::log_file),
                        "<LOGFILE>", "Path where the log file should be stored")
      .addOption({'d', "daemon"}, util::setBool(Flags::daemon),
                 "Become a daemon")
      .addOptionWithArg({'P', "pidfile"}, util::setString(Flags::pidfile),
                        "<PIDFILE>", "Path where the pidfile should be stored")
      .addOptionWithArg({'S', "store-dir"},
                        util::setString(Flags::store_directory), "<DIR>",
                        "Path where the files should be stored")
      .addOptionWithArg({'T', "temp-dir"},
                        util::setString(Flags::temp_directory), "<DIR>",
                        "Path where the sandboxes should be crated")
      .addOption({'k', "keep_sandboxes"}, util::setBool(Flags::keep_sandboxes),
                 "Keep the sandboxes after evaluation")
      .addOptionWithArg({'n', "num-cores"}, util::setInt(Flags::num_cores),
                        "<N>", "Number of cores to use")
      .addOptionWithArg({'s', "server"}, util::setString(Flags::server),
                        "<ADDRESS>", "Address to connect to")
      .addOptionWithArg({'p', "port"}, util::setInt(Flags::port), "<PORT>",
                        "Port to connect to")
      .addOptionWithArg({"name"}, util::setString(Flags::name), "<NAME>",
                        "Name of this worker")
      .addOptionWithArg({'t', "temp"}, util::setString(Flags::temp_directory),
                        "<TEMP>", "Where to store the sandboxes")
      .addOptionWithArg({'r', "pending-requests"},
                        util::setInt(Flags::pending_requests), "<REQS>",
                        "Maximum number of pending requests")
      .addOptionWithArg(
          {'c', "cache-size"}, util::setUint(Flags::cache_size), "<SZ>",
          "Maximum size of the cache, in megabytes. 0 means unlimited")
      .callAfterParsing(KJ_BIND_METHOD(*this, Run))
      .build();
}
}  // namespace worker
