#include "util/flags.hpp"

bool Flags::daemon = false;
std::string Flags::pidfile;
std::string Flags::store_directory = "files";
int32_t Flags::port = 7070;

std::string Flags::server;
std::string Flags::name = "unnamed_worker";
int32_t Flags::num_cores = 0;
std::string Flags::temp_directory = "temp";
bool Flags::keep_sandboxes = false;
int32_t Flags::pending_requests = 2;

std::string Flags::listen_address = "0.0.0.0";
uint32_t Flags::cache_size = 0;
