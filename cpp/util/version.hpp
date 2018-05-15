#include <string>

namespace util {
#ifdef TASK_MAKER_VERSION
const std::string version = TASK_MAKER_VERSION;
#else
const std::string version = "unknown";
#endif
}  // namespace util
