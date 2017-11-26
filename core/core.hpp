#ifndef CORE_CORE_HPP
#define CORE_CORE_HPP

#include "core/execution.hpp"
#include "core/file_id.hpp"

namespace core {

class Core {
 public:
  FileID* LoadFile(const std::string& description, const std::string& path) {
    files_to_load_.push_back(FileID(description, path));
    return &files_to_load_.back();
  }

  Execution* AddExecution(const std::string& description,
                          const std::string& executable,
                          const std::vector<std::string>& args) {
    executions_.push_back(Execution(description, executable, args));
    return &executions_.back();
  }

  bool Run();

 private:
  std::vector<FileID> files_to_load_;
  std::vector<Execution> executions_;
};

}  // namespace core

#endif
