#ifndef UTIL_FLAGS_HPP
#define UTIL_FLAGS_HPP
#include "gflags/gflags.h"
#include "glog/logging.h"

DECLARE_bool(daemon);
DECLARE_string(pidfile);

DECLARE_string(server);
DECLARE_string(name);
DECLARE_int32(num_cores);
DECLARE_string(store_directory);
DECLARE_string(temp_directory);

DECLARE_string(address);
DECLARE_int32(port);

DECLARE_string(mode);

#endif
