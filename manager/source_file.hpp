#ifndef MANAGER_SOURCE_FILE_HPP
#define MANAGER_SOURCE_FILE_HPP

#include "core/core.hpp"
#include "core/execution.hpp"
#include "manager/event_queue.hpp"
#include "proto/task.pb.h"

namespace manager {
class SourceFile {
 public:
  static std::unique_ptr<SourceFile> FromProto(EventQueue* queue,
                                               core::Core* core,
                                               const proto::SourceFile& source,
                                               bool fatal_failures = false);
  virtual core::Execution* execute(const std::string& description,
                                   const std::vector<std::string>& args) = 0;
  virtual ~SourceFile() = default;
  SourceFile(const SourceFile&) = delete;
  SourceFile(SourceFile&&) = delete;
  SourceFile& operator=(const SourceFile&) = delete;
  SourceFile& operator=(SourceFile&&) = delete;
};

}  // namespace manager

#endif
