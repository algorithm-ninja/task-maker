#ifndef UTIL_WHICH_HPP
#define UTIL_WHICH_HPP

#include <string>

namespace util {

// Equivalent to the command-line utility which. Uses caching to speed up
// lookups, unless explicitely disabled.
std::string which(const std::string& cmd, bool use_cache = true);

}  // namespace util

#endif
