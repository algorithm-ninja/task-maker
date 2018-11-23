#ifndef UTIL_WHICH_HPP
#define UTIL_WHICH_HPP

#include <string>

namespace util {

// Equivalent to the command-line utility which. Uses caching to speed up
// lookups, unless explicitly disabled.
// The cache behavior is very basical, if the file is found it's put in the
// cache, any other request to that file will come from the cache even if the
// file is no longer found.
// TODO consider checking whether the file exists if it cames from the cache
std::string which(const std::string& cmd, bool use_cache = true);

}  // namespace util

#endif
