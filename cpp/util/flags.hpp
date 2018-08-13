#ifndef UTIL_FLAGS_HPP
#define UTIL_FLAGS_HPP

#include <string>

struct Flags {
  static bool daemon;
  static std::string pidfile;

  static std::string server;
  static std::string name;
  static int32_t num_cores;

  static std::string store_directory;
  static std::string temp_directory;

  static std::string listen_address;
  static int32_t listen_port;
};

#endif
