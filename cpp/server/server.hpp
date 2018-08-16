#ifndef SERVER_SERVER_HPP
#define SERVER_SERVER_HPP

#include "capnp/server.capnp.h"
#include "server/dispatcher.hpp"
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
  util::SHA256_t hash = util::SHA256_t::ZERO;
};
};  // namespace detail

class Execution : public capnproto::Execution::Server {
 public:
  KJ_DISALLOW_COPY(Execution);
  Execution(server::Dispatcher& dispatcher, uint32_t& last_file_id,
            std::unordered_map<uint32_t, detail::FileInfo>& file_info,
            std::string description)
      : dispatcher_(dispatcher),
        last_file_id_(last_file_id),
        file_info_(file_info),
        description_(description) {}

  kj::Promise<void> setExecutablePath(SetExecutablePathContext context);
  kj::Promise<void> setExecutable(SetExecutableContext context);  // TODO
  kj::Promise<void> setStdin(SetStdinContext context);            // TODO
  kj::Promise<void> addInput(AddInputContext context);            // TODO
  kj::Promise<void> setArgs(SetArgsContext context);
  kj::Promise<void> disableCache(DisableCacheContext context);
  kj::Promise<void> makeExclusive(MakeExclusiveContext context);
  kj::Promise<void> setLimits(SetLimitsContext context);
  kj::Promise<void> stdout(StdoutContext context);
  kj::Promise<void> stderr(StderrContext context);
  kj::Promise<void> output(OutputContext context);
  kj::Promise<void> notifyStart(NotifyStartContext context);
  kj::Promise<void> getResult(GetResultContext context);  // TODO

 private:
  server::Dispatcher& dispatcher_;
  uint32_t& last_file_id_;
  std::unordered_map<uint32_t, detail::FileInfo>& file_info_;
  std::string description_;
  capnp::MallocMessageBuilder builder_;
  capnproto::Request::Builder request_ =
      builder_.initRoot<capnproto::Request>();
  std::vector<std::pair<std::string, uint32_t>> inputs;
  std::vector<std::pair<std::string, uint32_t>> outputs;
  uint32_t stdin_ = 0;
  uint32_t stdout_ = 0;
  uint32_t stderr_ = 0;
  uint32_t cache_enabled_ = true;
  std::vector<kj::PromiseFulfillerPair<void>> start_promises_;
};

class FrontendContext : public capnproto::FrontendContext::Server {
 public:
  KJ_DISALLOW_COPY(FrontendContext);
  FrontendContext(server::Dispatcher& dispatcher) : dispatcher_(dispatcher) {}
  kj::Promise<void> provideFile(ProvideFileContext context);
  kj::Promise<void> addExecution(AddExecutionContext context);
  kj::Promise<void> startEvaluation(StartEvaluationContext context);  // TODO
  kj::Promise<void> getFileContents(GetFileContentsContext context);  // TODO
  kj::Promise<void> stopEvaluation(StopEvaluationContext context);    // TODO

 private:
  server::Dispatcher& dispatcher_;
  uint32_t last_file_id_ = 1;
  std::unordered_map<uint32_t, detail::FileInfo> file_info_;
};

class Server : public capnproto::MainServer::Server {
 public:
  kj::Promise<void> registerFrontend(RegisterFrontendContext context);
  kj::Promise<void> registerEvaluator(RegisterEvaluatorContext context);
  friend class FrontendContext;

 private:
  Dispatcher dispatcher_;
};

}  // namespace server

#endif
