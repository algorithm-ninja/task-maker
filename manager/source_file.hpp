#ifndef MANAGER_SOURCE_FILE_HPP
#define MANAGER_SOURCE_FILE_HPP

#include <vector>
#include "core/core.hpp"
#include "core/execution.hpp"
#include "core/task_status.hpp"
#include "manager/event_queue.hpp"
#include "proto/task.pb.h"

namespace manager {
class SourceFile {
 public:
  static std::unique_ptr<SourceFile> FromProto(
      EventQueue* queue, core::Core* core, const proto::SourceFile& source,
      const proto::GraderInfo& grader, bool fatal_failures = false);
  virtual core::Execution* execute(const std::string& description,
                                   const std::vector<std::string>& args) = 0;
  virtual ~SourceFile() = default;
  SourceFile(const SourceFile&) = delete;
  SourceFile(SourceFile&&) = delete;
  SourceFile& operator=(const SourceFile&) = delete;
  SourceFile& operator=(SourceFile&&) = delete;

  bool FatalFailures() const { return fatal_failures_; }

 protected:
  SourceFile(core::Core* core, EventQueue* queue, bool fatal_failures)
    : core_(core), queue_(queue), fatal_failures_(fatal_failures) {};

  core::Core* core_;
  EventQueue* queue_;
  bool fatal_failures_;
};

class CompiledSourceFile : public SourceFile {
 public:
  CompiledSourceFile(EventQueue* queue,
                     core::Core* core,
                     const proto::SourceFile& source,
                     const proto::GraderInfo& grader,
                     bool fatal_failures = false);

  core::Execution* execute(const std::string& description,
                           const std::vector<std::string>& args);

 protected:
  core::Execution* compilation_;
  core::FileID* compiled_;
};

class NotCompiledSourceFile : public SourceFile {
 public:
  NotCompiledSourceFile(EventQueue* queue,
                        core::Core* core,
                        const proto::SourceFile& source,
                        bool fatal_failures = false);

  core::Execution* execute(const std::string& description,
                           const std::vector<std::string>& args);

 protected:
  std::vector<core::FileID*> runtime_deps_;
  core::FileID* program_;
};

}  // namespace manager

#endif
