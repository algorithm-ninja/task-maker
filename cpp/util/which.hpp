#ifndef UTIL_WHICH_HPP
#define UTIL_WHICH_HPP

#include <string>

namespace util {

std::string which(const std::string& cmd, bool use_cache = true);

}  // namespace util

#endif
