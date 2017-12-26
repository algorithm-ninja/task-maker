#ifndef MANAGER_EVALUATION_HPP
#define MANAGER_EVALUATION_HPP

#include "core/core.hpp"
#include "manager/event_queue.hpp"
#include "manager/generation.hpp"
#include "manager/source_file.hpp"
#include "proto/manager.pb.h"
#include "proto/task.pb.h"

namespace manager {

class Evaluation {
 public:
  Evaluation(EventQueue* queue, core::Core* core, const Generation& generation,
             const proto::Task& task, bool exclusive,
             proto::CacheMode cache_mode, const std::string& executor);

  void Evaluate(SourceFile* solution);
};

}  // namespace manager

#endif
