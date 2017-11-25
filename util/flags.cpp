#include "util/flags.hpp"

DEFINE_int32(
    num_cores, 0,
    "Number of cores to use for the local executor. If unset, autodetect");
DEFINE_string(store_directory, "files", "Where files should be stored");
DEFINE_string(temp_directory, "temp", "Where the sandboxes should be created");
