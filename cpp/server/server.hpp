#ifndef SERVER_SERVER_HPP
#define SERVER_SERVER_HPP

#include "capnp/server.capnp.h"
#include "server/dispatcher.hpp"

namespace server {

class Server;

class FrontendContext : public capnproto::FrontendContext::Server {
 public:
  KJ_DISALLOW_COPY(FrontendContext);
  FrontendContext(server::Server& server) : server_(server) {}
  kj::Promise<void> provideFile(ProvideFileContext context) {
    return kj::READY_NOW;
  }
  kj::Promise<void> addExecution(AddExecutionContext context) {
    return kj::READY_NOW;
  }
  kj::Promise<void> startEvaluation(StartEvaluationContext context) {
    return kj::READY_NOW;
  }
  kj::Promise<void> getFileContents(GetFileContentsContext context) {
    return kj::READY_NOW;
  }
  kj::Promise<void> stopEvaluation(StopEvaluationContext context) {
    return kj::READY_NOW;
  }

 private:
  server::Server& server_;
  uint32_t last_file_id_;
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
