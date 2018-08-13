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

inline std::vector<std::string> split(const std::string& s, char delim) {
  std::vector<std::string> elems;
  split(s, delim, std::back_inserter(elems));
  return elems;
}

inline std::function<bool()> setBool(bool& var) {
  return [&var]() {
    var = true;
    return true;
  };
};

inline std::function<bool(kj::StringPtr)> setString(std::string& var) {
  return [&var](kj::StringPtr p) {
    var = p;
    return true;
  };
};

inline std::function<bool(kj::StringPtr)> setInt(int& var) {
  return [&var](kj::StringPtr p) {
    var = std::stoi(std::string(p));
    return true;
  };
};

}  // namespace util
#endif
