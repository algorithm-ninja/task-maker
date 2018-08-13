#include "util/which.hpp"
#include <cstdlib>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>
#include "util/file.hpp"
#include "util/misc.hpp"

namespace {
std::unordered_map<std::string, std::string> cmd_cache;
}  // namespace

namespace util {

std::string which(const std::string& cmd, bool use_cache) {
  static const std::string path = std::getenv("PATH");
  static const std::vector<std::string> dirs = split(path, ':');

  if (use_cache && cmd_cache.count(cmd) > 0) return cmd_cache[cmd];

  for (const std::string& dir : dirs) {
    std::string fullpath = util::File::JoinPath(dir, cmd);
    if (File::Exists(fullpath)) return cmd_cache[cmd] = fullpath;
  }

  return cmd_cache[cmd] = "";
}

}  // namespace util
