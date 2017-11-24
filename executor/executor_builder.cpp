#include "executor/executor_builder.hpp"

#include "executor/local_executor.hpp"

#include <memory>

namespace executor {

namespace {
class LocalExecutorCtx : public LocalExecutor {
 public:
  LocalExecutorCtx(const ExecutorOptions& options) : LocalExecutor(options) {}
};
}  // namespace

std::unique_ptr<Executor> ExecutorBuilder::Get(const ExecutorOptions& options) {
  if (options.kind == ExecutorOptions::Kind::LOCAL) {
    return std::unique_ptr<LocalExecutorCtx>(new LocalExecutorCtx(options));
  }
  return nullptr;
}
}  // namespace executor
