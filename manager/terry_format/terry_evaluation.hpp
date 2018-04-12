#ifndef MANAGER_TERRY_EVALUATION_HPP
#define MANAGER_TERRY_EVALUATION_HPP

#include "manager/evaluation.hpp"
#include "manager/terry_format/terry_generation.hpp"

namespace manager {

class TerryEvaluation : public Evaluation {
 public:
  TerryEvaluation(EventQueue* queue, core::Core* core,
                  TerryGeneration* generation, proto::TerryTask task,
                  bool exclusive, proto::CacheMode cache_mode,
                  std::string executor, bool keep_sandbox);

  void Evaluate(SourceFile* solution, int64_t seed);

 private:
  EventQueue* queue_;
  core::Core* core_;
  TerryGeneration* generation_;
  proto::TerryTask task_;
  bool exclusive_;
  proto::CacheMode cache_mode_;
  std::string executor_;
  bool keep_sandbox_;
};

}  // namespace manager

#endif  // MANAGER_TERRY_EVALUATION_HPP
