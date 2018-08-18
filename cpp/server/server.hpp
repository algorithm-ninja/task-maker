#ifndef SERVER_SERVER_HPP
#define SERVER_SERVER_HPP

#include "capnp/server.capnp.h"
#include "server/dispatcher.hpp"
#include "util/misc.hpp"
#include "util/sha256.hpp"

#include <capnp/message.h>
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
};
};  // namespace detail

class FrontendContext;

class File : public capnproto::File::Server {
 public:
  File(uint32_t id) : id_(id) {}
  kj::Promise<void> getId(GetIdContext context);

 private:
  uint32_t id_;
};

class Execution : public capnproto::Execution::Server {
 public:
  KJ_DISALLOW_COPY(Execution);
  Execution(FrontendContext& frontend_context, std::string description)
      : frontend_context_(frontend_context), description_(description) {}

  kj::Promise<void> setExecutablePath(SetExecutablePathContext context);
  kj::Promise<void> setExecutable(SetExecutableContext context);
  kj::Promise<void> setStdin(SetStdinContext context);
  kj::Promise<void> addInput(AddInputContext context);
  kj::Promise<void> setArgs(SetArgsContext context);
  kj::Promise<void> disableCache(DisableCacheContext context);
  kj::Promise<void> makeExclusive(MakeExclusiveContext context);
  kj::Promise<void> setLimits(SetLimitsContext context);
  kj::Promise<void> stdout(StdoutContext context);
  kj::Promise<void> stderr(StderrContext context);
  kj::Promise<void> output(OutputContext context);
  kj::Promise<void> notifyStart(NotifyStartContext context);
  kj::Promise<void> getResult(GetResultContext context);

 private:
  FrontendContext& frontend_context_;
  std::string description_;
  capnp::MallocMessageBuilder builder_;
  capnproto::Request::Builder request_ =
      builder_.initRoot<capnproto::Request>();
  std::unordered_map<std::string, uint32_t> inputs_;
  std::unordered_map<std::string, uint32_t> outputs_;
  uint32_t executable_ = 0;
  uint32_t stdin_ = 0;
  uint32_t stdout_ = 0;
  uint32_t stderr_ = 0;
  uint32_t cache_enabled_ = true;
  kj::PromiseFulfillerPair<void> start_ = kj::newPromiseAndFulfiller<void>();
  kj::ForkedPromise<void> forked_start_ = start_.promise.fork();
  kj::PromiseFulfillerPair<void> finish_promise_ =
      kj::newPromiseAndFulfiller<void>();
};

class FrontendContext : public capnproto::FrontendContext::Server {
 public:
  KJ_DISALLOW_COPY(FrontendContext);
  FrontendContext(server::Dispatcher& dispatcher) : dispatcher_(dispatcher) {}
  kj::Promise<void> provideFile(ProvideFileContext context);
  kj::Promise<void> addExecution(AddExecutionContext context);
  kj::Promise<void> startEvaluation(StartEvaluationContext context);
  kj::Promise<void> getFileContents(GetFileContentsContext context);
  kj::Promise<void> stopEvaluation(StopEvaluationContext context);

 private:
  friend class Execution;
  server::Dispatcher& dispatcher_;
  uint32_t last_file_id_ = 1;
  std::unordered_map<uint32_t, detail::FileInfo> file_info_;
  util::UnionPromiseBuilder builder_;
  kj::PromiseFulfillerPair<void> evaluation_start_ =
      kj::newPromiseAndFulfiller<void>();
  kj::ForkedPromise<void> forked_evaluation_start_ =
      evaluation_start_.promise.fork();
  kj::PromiseFulfillerPair<void> evaluation_early_stop_ =
      kj::newPromiseAndFulfiller<void>();
};

class Server : public capnproto::MainServer::Server {
 public:
  kj::Promise<void> registerFrontend(RegisterFrontendContext context);
  kj::Promise<void> registerEvaluator(RegisterEvaluatorContext context);
  kj::Promise<void> requestFile(RequestFileContext context);
  friend class FrontendContext;

 private:
  Dispatcher dispatcher_;
};

}  // namespace server

#endif
