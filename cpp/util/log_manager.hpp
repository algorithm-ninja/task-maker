#ifndef UTIL_LOG_MANAGER_HPP
#define UTIL_LOG_MANAGER_HPP
#include <kj/exception.h>
#include <kj/main.h>
#include <ostream>
#include "backward.hpp"

namespace util {

class LogManager : public kj::ExceptionCallback {
 public:
  LogManager(kj::ProcessContext& context);
  void logMessage(kj::LogSeverity severity, const char* file, int line,
                  int contextDepth, kj::String&& text) override;
  void onRecoverableException(kj::Exception&& exception) override;
  void onFatalException(kj::Exception&& exception) override;
  StackTraceMode stackTraceMode() override { return StackTraceMode::NONE; }

 private:
  std::ostream& out;
  backward::SignalHandling sh;  // Override kj's signal handling.
};
}  // namespace util

#endif
