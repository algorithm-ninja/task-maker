#ifndef EXECUTOR_EXECUTOR_BUILDER_HPP
#define EXECUTOR_EXECUTOR_BUILDER_HPP
#include "executor/executor.hpp"

#include <memory>

namespace executor {

class ExecutorBuilder {
 public:
  static std::shared_ptr<Executor> Get(const ExecutorOptions& options);
};

}  // namespace executor

#endif
