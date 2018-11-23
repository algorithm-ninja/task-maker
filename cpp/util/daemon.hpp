#ifndef UTIL_DAEMON_HPP
#define UTIL_DAEMON_HPP

#include <string>

namespace util {

// Daemonizes the current process. The PID of the process will be written to
// pidfile. If pidfile is an empty string, scope is used to automatically
// generate a pidfile path.
void daemonize(const std::string& scope, std::string pidfile = "");

}  // namespace util
#endif  // UTIL_DAEMON_HPP
