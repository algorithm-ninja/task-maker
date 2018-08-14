#include "server/server.hpp"

#include <kj/debug.h>

#include <string>

namespace server {

kj::Promise<void> Server::registerFrontend(RegisterFrontendContext context) {
  KJ_ASSERT(false, "Not implemented yet");
}

kj::Promise<void> Server::registerEvaluator(RegisterEvaluatorContext context) {
  KJ_LOG(INFO,
         "Worker " + std::string(context.getParams().getName()) + " connected");
  return kj::READY_NOW;
}

}  // namespace server
