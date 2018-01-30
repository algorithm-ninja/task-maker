#include "absl/strings/str_split.h"
#include "cstdlib"
#include "string"
#include "unordered_map"
#include "util/file.hpp"
#include "util/which.hpp"
#include <sys/stat.h>

namespace {
std::unordered_map<std::string, std::string> cmd_cache;

bool file_exists(const std::string& path) {
  struct stat buffer{};
  return stat(path.c_str(), &buffer) == 0;
}
}  // namespace

namespace util {

std::string which(const std::string& cmd) {
  static const std::string path = std::getenv("PATH");
  static const std::vector<std::string> dirs = absl::StrSplit(path, ":");

  if (cmd_cache.count(cmd) > 0)
    return cmd_cache[cmd];

  for (const std::string& dir : dirs) {
    std::string fullpath = util::File::JoinPath(dir, cmd);
    if (file_exists(fullpath))
      return cmd_cache[cmd] = fullpath;
  }

  return cmd_cache[cmd] = "";
}

}  // namespace util
