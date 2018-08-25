#ifndef UTIL_FLAGS_HPP
#define UTIL_FLAGS_HPP

#include <string>

struct Flags {
  // Common flags
  static bool daemon;
  static std::string pidfile;
  static std::string store_directory;
  static int32_t port;
  static uint32_t cache_size;

  // Worker-only flags
  static std::string server;
  static std::string name;
  static int32_t num_cores;
  static bool keep_sandboxes;
  static std::string temp_directory;
  static int32_t pending_requests;

  // Server-only flags
  static std::string listen_address;
};

#endif
