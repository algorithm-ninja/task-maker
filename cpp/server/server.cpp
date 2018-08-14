#include "server/server.hpp"

#include <kj/debug.h>

#include <string>

namespace server {

kj::Promise<void> Server::registerFrontend(RegisterFrontendContext context) {
  // TODO: here, we assume that capnproto keeps the FrontendContext alive
  // as long as the client still call its methods, which seems reasonable but
  // could not be the case.
  context.getResults().setContext(kj::heap<FrontendContext>(*this));
  return kj::READY_NOW;
}

kj::Promise<void> Server::registerEvaluator(RegisterEvaluatorContext context) {
  KJ_LOG(INFO,
         "Worker " + std::string(context.getParams().getName()) + " connected");
  return dispatcher_.AddEvaluator(context.getParams().getEvaluator());
}

}  // namespace server
