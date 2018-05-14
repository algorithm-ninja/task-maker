#include "util/which.hpp"
#include <sys/stat.h>
#include <cstdlib>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#include "util/file.hpp"

namespace {
std::unordered_map<std::string, std::string> cmd_cache;

bool file_exists(const std::string& path) {
  struct stat buffer {};
  return stat(path.c_str(), &buffer) == 0;
}

template <typename Out>
void split(const std::string& s, char delim, Out result) {
  std::stringstream ss(s);
  std::string item;
  while (std::getline(ss, item, delim)) {
    if (!item.empty()) *(result++) = item;
  }
}

std::vector<std::string> split(const std::string& s, char delim) {
  std::vector<std::string> elems;
  split(s, delim, std::back_inserter(elems));
  return elems;
}
}  // namespace

namespace util {

std::string which(const std::string& cmd, bool use_cache) {
  static const std::string path = std::getenv("PATH");
  static const std::vector<std::string> dirs = split(path, ':');

  if (use_cache && cmd_cache.count(cmd) > 0) return cmd_cache[cmd];

  for (const std::string& dir : dirs) {
    std::string fullpath = util::File::JoinPath(dir, cmd);
    if (file_exists(fullpath)) return cmd_cache[cmd] = fullpath;
  }

  return cmd_cache[cmd] = "";
}

}  // namespace util
