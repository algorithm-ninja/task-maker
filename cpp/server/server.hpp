#ifndef SERVER_SERVER_HPP
#define SERVER_SERVER_HPP

#include "capnp/server.capnp.h"
#include "server/cache.hpp"
#include "server/dispatcher.hpp"
#include "util/sha256.hpp"
#include "util/union_promise.hpp"

#include <capnp/message.h>
#include <memory>
#include <unordered_map>

namespace server {

namespace detail {
struct FileInfo {
  uint32_t id = 0;
  std::string description;
  bool executable = false;
  bool provided = false;
  kj::PromiseFulfillerPair<void> promise = kj::newPromiseAndFulfiller<void>();
  kj::ForkedPromise<void> forked_promise = promise.promise.fork();
  util::SHA256_t hash = util::SHA256_t::ZERO;
  util::UnionPromiseBuilder dependencies_propagated_;
};
};  // namespace detail

// Implementations of the server interface.

class FrontendContext;
class ExecutionGroup;

class Execution : public capnproto::Execution::Server {
 public:
  Execution(FrontendContext* frontend_context, std::string description,
            ExecutionGroup* group);

  kj::Promise<void> setExecutablePath(
      SetExecutablePathContext context) override;
  kj::Promise<void> setExecutable(SetExecutableContext context) override;
  kj::Promise<void> setStdin(SetStdinContext context) override;
  kj::Promise<void> addInput(AddInputContext context) override;
  kj::Promise<void> setArgs(SetArgsContext context) override;
  kj::Promise<void> disableCache(DisableCacheContext context) override;
  kj::Promise<void> makeExclusive(MakeExclusiveContext context) override;
  kj::Promise<void> setLimits(SetLimitsContext context) override;
  kj::Promise<void> setExtraTime(SetExtraTimeContext context) override;
  kj::Promise<void> addFifo(AddFifoContext context) override;
  kj::Promise<void> setStdinFifo(SetStdinFifoContext context) override;
  kj::Promise<void> setStdoutFifo(SetStdoutFifoContext context) override;
  kj::Promise<void> setStderrFifo(SetStderrFifoContext context) override;
  kj::Promise<void> getStdout(GetStdoutContext context) override;
  kj::Promise<void> getStderr(GetStderrContext context) override;
  kj::Promise<void> getOutput(GetOutputContext context) override;
  kj::Promise<void> notifyStart(NotifyStartContext context) override;
  kj::Promise<void> getResult(GetResultContext context) override;

 private:
  void addDependencies(util::UnionPromiseBuilder* dependencies);
  void prepareRequest();
  void processResult(capnproto::ProcessResult::Reader result,
                     util::UnionPromiseBuilder* dependencies_propagated,
                     bool from_cache = false);
  void onDependenciesFailure(kj::Exception exc);
  void onDependenciesPropagated();

  FrontendContext& frontend_context_;
  std::string description_;
  capnp::MallocMessageBuilder builder_;
  capnproto::ProcessRequest::Builder request_ =
      builder_.initRoot<capnproto::ProcessRequest>();
  std::unordered_map<std::string, uint32_t> inputs_;
  std::unordered_map<std::string, uint32_t> outputs_;
  std::unordered_map<std::string, uint32_t> fifos_;
  uint32_t executable_ = 0;
  uint32_t stdin_ = 0;
  uint32_t stdin_fifo_ = 0;
  uint32_t stdout_ = 0;
  uint32_t stdout_fifo_ = 0;
  uint32_t stderr_ = 0;
  uint32_t stderr_fifo_ = 0;
  kj::PromiseFulfillerPair<void> finish_promise_ =
      kj::newPromiseAndFulfiller<void>();
  friend class ExecutionGroup;
  ExecutionGroup& group_;
  kj::Maybe<GetResultContext> context_;
};

class ExecutionGroup : public capnproto::ExecutionGroup::Server {
 public:
  void Register(Execution* ex);
  ExecutionGroup(FrontendContext* frontend_context, std::string description)
      : frontend_context_(*frontend_context),
        description_(std::move(description)) {}
  void setExclusive();
  void disableCache();

  kj::Promise<void> addExecution(AddExecutionContext context) override;
  kj::Promise<void> createFifo(CreateFifoContext context) override;

  // Utility methods
  kj::Promise<void> notifyStart();
  kj::Promise<void> Finalize(Execution* ex);

 private:
  FrontendContext& frontend_context_;
  std::string description_;
  std::vector<Execution*> executions_;
  kj::Promise<void> done_ = kj::READY_NOW;
  kj::ForkedPromise<void> forked_done_ = done_.fork();
  bool finalized_ = false;
  capnp::MallocMessageBuilder builder_;
  capnproto::Request::Builder request_ =
      builder_.initRoot<capnproto::Request>();
  uint32_t cache_enabled_ = true;
  kj::PromiseFulfillerPair<void> start_ = kj::newPromiseAndFulfiller<void>();
  kj::ForkedPromise<void> forked_start_ = start_.promise.fork();
  size_t next_fifo_ = 1;
};

class FrontendContext : public capnproto::FrontendContext::Server {
 public:
  FrontendContext(Dispatcher* dispatcher, CacheManager* cache_manager)
      : dispatcher_(*dispatcher),
        builder_(false),
        cache_manager_(*cache_manager) {}
  ~FrontendContext() { *canceled_ = true; }
  FrontendContext(const FrontendContext&) = delete;
  FrontendContext(FrontendContext&&) = delete;
  FrontendContext& operator=(const FrontendContext&) = delete;
  FrontendContext& operator=(FrontendContext&&) = delete;
  kj::Promise<void> provideFile(ProvideFileContext context) override;
  kj::Promise<void> addExecution(AddExecutionContext context) override;
  kj::Promise<void> addExecutionGroup(
      AddExecutionGroupContext context) override;
  kj::Promise<void> startEvaluation(StartEvaluationContext context) override;
  kj::Promise<void> getFileContents(GetFileContentsContext context) override;
  kj::Promise<void> stopEvaluation(StopEvaluationContext context) override;

 private:
  friend class Execution;
  friend class ExecutionGroup;
  server::Dispatcher& dispatcher_;
  static uint32_t num_frontends_;
  uint32_t frontend_id_ = num_frontends_++;
  uint32_t last_file_id_ = 1;
  std::unordered_map<uint32_t, detail::FileInfo> file_info_;
  util::UnionPromiseBuilder builder_;
  kj::PromiseFulfillerPair<void> evaluation_start_ =
      kj::newPromiseAndFulfiller<void>();
  kj::ForkedPromise<void> forked_evaluation_start_ =
      evaluation_start_.promise.fork();
  kj::PromiseFulfillerPair<void> evaluation_early_stop_ =
      kj::newPromiseAndFulfiller<void>();
  kj::ForkedPromise<void> forked_early_stop_ =
      evaluation_early_stop_.promise.fork();
  uint32_t ready_tasks_ = 0;
  uint32_t scheduled_tasks_ = 0;
  CacheManager& cache_manager_;
  std::vector<kj::Own<ExecutionGroup>> groups_;
  std::shared_ptr<bool> canceled_ = std::make_shared<bool>(false);
};

class Server : public capnproto::MainServer::Server {
 public:
  kj::Promise<void> registerFrontend(RegisterFrontendContext context) override;
  kj::Promise<void> registerEvaluator(
      RegisterEvaluatorContext context) override;
  kj::Promise<void> requestFile(RequestFileContext context) override;
  friend class FrontendContext;

 private:
  Dispatcher dispatcher_;
  CacheManager cache_manager_;
};

}  // namespace server

#endif
