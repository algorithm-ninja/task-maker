#include "util/log_manager.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include "util/file.hpp"
#include "util/flags.hpp"

namespace util {
namespace {
std::ostream& ChooseOut() {
  if (Flags::log_file != "") {
    static std::ofstream of(Flags::log_file);
    return of;
  } else {
    return std::cerr;
  }
}

static const constexpr char* log_msg[] = {"INFO", "WARNING", "ERROR", "FATAL",
                                          "DBG"};
static const constexpr char* colors[] = {"\e[0;32m", "\e[0;33m", "\e[0;31m",
                                         "\e[7;31m", "\e[0;35m"};
const constexpr char* reset_color = "\e[m";
const constexpr char* file_color = "\e[0;34m";
const constexpr char* date_color = "\e[0;36m";

constexpr bool strings_equal(char const* a, char const* b) {
  return *a == *b && (*a == '\0' || strings_equal(a + 1, b + 1));
}

#define CHECK_MSG(lvl)                                                   \
  static_assert(strings_equal(#lvl, log_msg[(int)kj::LogSeverity::lvl]), \
                #lvl " has a wrong log message!");

CHECK_MSG(INFO);
CHECK_MSG(WARNING);
CHECK_MSG(ERROR);
CHECK_MSG(FATAL);
CHECK_MSG(DBG);

}  // namespace

void LogManager::onRecoverableException(kj::Exception&& exception) {
  logMessage(kj::LogSeverity::WARNING, exception.getFile(), exception.getLine(),
             0, kj::heapString(exception.getDescription()));
  if (::kj::_::Debug::shouldLog(kj::LogSeverity::INFO)) {
    backward::StackTrace s;
    s.load_here();
    backward::Printer p;
    p.color_mode = backward::ColorMode::always;
    p.print(s, out);
  }

  next.onRecoverableException(kj::mv(exception));
}
void LogManager::onFatalException(kj::Exception&& exception) {
  logMessage(kj::LogSeverity::FATAL, exception.getFile(), exception.getLine(),
             0, kj::heapString(exception.getDescription()));
  if (::kj::_::Debug::shouldLog(kj::LogSeverity::INFO)) {
    backward::StackTrace s;
    s.load_here();
    backward::Printer p;
    p.color_mode = backward::ColorMode::always;
    p.print(s, out);
  }
  next.onFatalException(kj::mv(exception));
}

LogManager::LogManager(kj::ProcessContext& context) : out(ChooseOut()) {
  if (!out) {
    context.exitError("Invalid log file provided!");
  }
}

void LogManager::logMessage(kj::LogSeverity severity, const char* file,
                            int line, int contextDepth, kj::String&& text) {
  auto t = std::time(nullptr);
  auto tm = *std::localtime(&t);
  out << date_color << std::put_time(&tm, "%Y-%m-%d %H:%M:%S") << reset_color
      << " ";
  out << std::string(colors[(int)severity]) + log_msg[(int)severity][0] +
             reset_color + " ";
  out << std::left << std::setw(35)
      << file_color + util::File::BaseName(file) + ":" + std::to_string(line) +
             reset_color;
  out << text.cStr() << std::endl;
}
}  // namespace util
