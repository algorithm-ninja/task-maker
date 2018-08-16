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
  bool executable;
  kj::PromiseFulfillerPair<void> promise;
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
  server::Dispatcher& dispatcher_;
  uint32_t& last_file_id_;
  std::unordered_map<uint32_t, detail::FileInfo>& file_info_;
  std::string description_;
  capnp::MallocMessageBuilder builder_;
  capnproto::Request::Builder request_ =
      builder_.initRoot<capnproto::Request>();
  std::vector<std::pair<std::string, int>> inputs;
  std::vector<std::pair<std::string, int>> outputs;
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
  server::Dispatcher& dispatcher_;
  uint32_t last_file_id_;
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
