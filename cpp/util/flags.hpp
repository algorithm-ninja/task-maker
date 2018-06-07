#ifndef UTIL_FLAGS_HPP
#define UTIL_FLAGS_HPP

#include <string>
#include "CLI11.hpp"

extern bool FLAGS_daemon;
extern std::string FLAGS_pidfile;

extern std::string FLAGS_server;
extern std::string FLAGS_name;
extern int32_t FLAGS_num_cores;

extern std::string FLAGS_store_directory;
extern std::string FLAGS_temp_directory;

extern std::string FLAGS_address;
extern int32_t FLAGS_manager_port;
extern int32_t FLAGS_server_port;

extern int32_t FLAGS_verbose;

namespace util {
extern CLI::App* manager_parser;
extern CLI::App* server_parser;
extern CLI::App* worker_parser;

void parse_flags(int argc, char** argv);
}  // namespace util

#endif
