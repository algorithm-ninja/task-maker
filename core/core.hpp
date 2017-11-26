#ifndef CORE_CORE_HPP
#define CORE_CORE_HPP

#include "core/execution.hpp"
#include "core/file_id.hpp"

namespace core {

class Core {
 public:
  FileID* LoadFile(const std::string& description, const std::string& path) {
    files_to_load_.push_back(
        std::unique_ptr<FileID>(new FileID(description, path)));
    return files_to_load_.back().get();
  }

  Execution* AddExecution(const std::string& description,
                          const std::string& executable,
                          const std::vector<std::string>& args) {
    executions_.push_back(std::unique_ptr<Execution>(
        new Execution(description, executable, args)));
    return executions_.back().get();
  }

  bool Run();

 private:
  std::vector<std::unique_ptr<FileID>> files_to_load_;
  std::vector<std::unique_ptr<Execution>> executions_;
};

}  // namespace core

#endif
