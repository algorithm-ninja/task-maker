#ifndef MANAGER_TERRY_GENERATION_HPP
#define MANAGER_TERRY_GENERATION_HPP

#include "core/core.hpp"
#include "manager/event_queue.hpp"
#include "manager/generation.hpp"
#include "manager/source_file.hpp"
#include "proto/manager.pb.h"
#include "proto/task.pb.h"

namespace manager {

class TerryGeneration : public Generation {
 public:
  TerryGeneration(EventQueue* queue, core::Core* core,
                  const proto::TerryTask& task, proto::CacheMode cache_mode,
                  const std::string& executor, bool keep_sandbox);

  SourceFile* GetGenerator() { return generator_.get(); }
  SourceFile* GetValidator() { return validator_.get(); }
  SourceFile* GetChecker() { return checker_.get(); }

 private:
  std::unique_ptr<SourceFile> generator_;
  std::unique_ptr<SourceFile> validator_;
  std::unique_ptr<SourceFile> checker_;
};

}  // namespace manager

#endif  // MANAGER_TERRY_GENERATION_HPP
