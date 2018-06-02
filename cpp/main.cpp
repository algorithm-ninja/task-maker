#include "manager/manager.hpp"
#include "remote/server.hpp"
#include "remote/worker.hpp"
#include "util/flags.hpp"

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);  // NOLINT
  google::InstallFailureSignalHandler();
  if (FLAGS_mode == "manager") {
    return manager_main();
  }
  if (FLAGS_mode == "server") {
    return server_main();
  }
  if (FLAGS_mode == "worker") {
    return worker_main();
  }
  fprintf(stderr, "Invalid program mode: %s\n", FLAGS_mode.c_str());
}
