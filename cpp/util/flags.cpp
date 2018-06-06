#include "util/flags.hpp"

DEFINE_bool(daemon, false, "become a daemon");  // NOLINT
DEFINE_string(pidfile, "", "path where to store the pidfile");

DEFINE_string(server, "", "server to connect to");  // NOLINT
DEFINE_string(name, "unnamed_worker",               // NOLINT
              "name that identifies this worker");
DEFINE_int32(  // NOLINT
    num_cores, 0,
    "Number of cores to use for the local executor. If unset, autodetect");
DEFINE_string(store_directory, "files",  // NOLINT
              "Where files should be stored");
DEFINE_string(temp_directory, "temp",  // NOLINT
              "Where the sandboxes should be created");

DEFINE_string(address, "0.0.0.0", "address to listen on");  // NOLINT
DEFINE_int32(port, 7071, "port to listen on");              // NOLINT

DEFINE_string(
    mode, "",
    "Which program should be executed. Valid values: manager, server, worker");
