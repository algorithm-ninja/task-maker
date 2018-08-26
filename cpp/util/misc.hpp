#ifndef UTIL_MISC_HPP
#define UTIL_MISC_HPP
#include <functional>
#include <sstream>
#include <string>
#include <vector>

#include <kj/string.h>

namespace util {

template <typename Out>
void split(const std::string& s, char delim, Out result) {
  std::stringstream ss(s);
  std::string item;
  while (std::getline(ss, item, delim)) {
    if (!item.empty()) *(result++) = item;
  }
}
std::vector<std::string> split(const std::string& s, char delim);

std::function<bool()> setBool(bool& var);
std::function<bool(kj::StringPtr)> setString(std::string& var);
std::function<bool(kj::StringPtr)> setInt(int& var);
std::function<bool(kj::StringPtr)> setUint(uint32_t& var);

void print_memory_chunk(const void* data, size_t size,
                        size_t bytes_per_line = 20);
#define PRINT_MEMORY_CHUNK(v) util::print_memory_chunk(&v, sizeof(v))

}  // namespace util
#endif
