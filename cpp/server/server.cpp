#include "server/server.hpp"

#include <kj/debug.h>

#include <string>

namespace server {
kj::Promise<void> Execution::setExecutablePath(
    SetExecutablePathContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setExecutable(SetExecutableContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setStdin(SetStdinContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::addInput(AddInputContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setArgs(SetArgsContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::disableCache(DisableCacheContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::makeExclusive(MakeExclusiveContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setLimits(SetLimitsContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::stdout(StdoutContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::stderr(StderrContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::output(OutputContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::notifyStart(NotifyStartContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> Execution::getResults(GetResultContext context) {
  return kj::READY_NOW;
}

kj::Promise<void> FrontendContext::provideFile(ProvideFileContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::addExecution(AddExecutionContext context) {
  // TODO: see Server::registerFrontend
  context.getResults().setExecution(
      kj::heap<Execution>(dispatcher_, last_file_id_, file_info_,
                          context.getParams().getDescription()));
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::startEvaluation(
    StartEvaluationContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::getFileContents(
    GetFileContentsContext context) {
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::stopEvaluation(
    StopEvaluationContext context) {
  return kj::READY_NOW;
}

kj::Promise<void> Server::registerFrontend(RegisterFrontendContext context) {
  // TODO: here, we assume that capnproto keeps the FrontendContext alive
  // as long as the client still call its methods, which seems reasonable but
  // could not be the case.
  context.getResults().setContext(kj::heap<FrontendContext>(dispatcher_));
  return kj::READY_NOW;
}

kj::Promise<void> Server::registerEvaluator(RegisterEvaluatorContext context) {
  KJ_LOG(INFO,
         "Worker " + std::string(context.getParams().getName()) + " connected");
  return dispatcher_.AddEvaluator(context.getParams().getEvaluator());
}

}  // namespace server
