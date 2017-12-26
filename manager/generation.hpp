#ifndef MANAGER_GENERATION_HPP
#define MANAGER_GENERATION_HPP

#include "core/core.hpp"
#include "core/file_id.hpp"
#include "manager/event_queue.hpp"
#include "manager/source_file.hpp"
#include "proto/manager.pb.h"
#include "proto/task.pb.h"

namespace manager {

class Generation {
 public:
  Generation(EventQueue* queue, core::Core* core, const proto::Task& task,
             proto::CacheMode cache_mode, const std::string& executor);

  core::FileID* GetInput(int64_t testcase_id) const;
  core::FileID* GetOutput(int64_t testcase_id) const;
  SourceFile* GetChecker() const;

  // To be called after Core.Run
  void WriteInputs(const std::string& destination);
  void WriteOutputs(const std::string& destination);
  void WriteChecker(const std::string& destionation);
};

}  // namespace manager

#endif
