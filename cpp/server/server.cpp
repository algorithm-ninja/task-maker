#include "server/server.hpp"
#include "util/file.hpp"

#include <kj/debug.h>

#include <string>

namespace server {
namespace {
uint32_t AddFileInfo(uint32_t& last_file_id,
                     std::unordered_map<uint32_t, detail::FileInfo>& info,
                     capnproto::File::Builder builder, bool executable,
                     const std::string& description) {
  uint32_t id = last_file_id++;
  info[id].id = id;
  info[id].description = description;
  info[id].executable = executable;
  builder.setId(id);
  return id;
}
}  // namespace

kj::Promise<void> Execution::setExecutablePath(
    SetExecutablePathContext context) {
  request_.getExecutable().setAbsolutePath(context.getParams().getPath());
  executable_ = 0;
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setExecutable(SetExecutableContext context) {
  executable_ = context.getParams().getFile().getId();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setStdin(SetStdinContext context) {
  stdin_ = context.getParams().getFile().getId();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::addInput(AddInputContext context) {
  inputs_.emplace_back(context.getParams().getFile().getId(),
                       context.getParams().getName());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setArgs(SetArgsContext context) {
  request_.setArgs(context.getParams().getArgs());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::disableCache(DisableCacheContext context) {
  cache_enabled_ = false;
  return kj::READY_NOW;
}
kj::Promise<void> Execution::makeExclusive(MakeExclusiveContext context) {
  request_.setExclusive(true);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setLimits(SetLimitsContext context) {
  request_.setLimits(context.getParams().getLimits());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::stdout(StdoutContext context) {
  stdout_ = AddFileInfo(
      frontend_context_.last_file_id_, frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Standard output of execution " + description_);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::stderr(StderrContext context) {
  stderr_ = AddFileInfo(
      frontend_context_.last_file_id_, frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Standard error of execution " + description_);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::output(OutputContext context) {
  uint32_t id = AddFileInfo(
      frontend_context_.last_file_id_, frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Output " + std::string(context.getParams().getName()) +
          " of execution " + description_);
  outputs_.emplace_back(context.getParams().getName(), id);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::notifyStart(NotifyStartContext context) {
  start_promises_.emplace_back(kj::newPromiseAndFulfiller<void>());
  return std::move(start_promises_.back().promise);
}
kj::Promise<void> Execution::getResult(GetResultContext context) {
  return kj::READY_NOW;
}

kj::Promise<void> FrontendContext::provideFile(ProvideFileContext context) {
  uint32_t id =
      AddFileInfo(last_file_id_, file_info_, context.getResults().initFile(),
                  context.getParams().getIsExecutable(),
                  context.getParams().getDescription());
  file_info_[id].provided = true;
  file_info_[id].hash = context.getParams().getHash();
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::addExecution(AddExecutionContext context) {
  // TODO: see Server::registerFrontend
  context.getResults().setExecution(
      kj::heap<Execution>(*this, context.getParams().getDescription()));
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::startEvaluation(
    StartEvaluationContext context) {
  evaluation_start_.fulfiller->fulfill();  // Starts the evaluation
  for (auto& file : file_info_) {
    if (file.second.provided) {
      builder_.AddPromise(
          util::File::MaybeGet(file.second.hash,
                               context.getParams().getSender())
              .eagerlyEvaluate(nullptr)
              .then([fulfiller =
                         std::move(file.second.promise.fulfiller)]() mutable {
                fulfiller->fulfill();
              }));
    }
    // Wait for all files to be ready
    builder_.AddPromise(file.second.forked_promise.addBranch());
  }
  return std::move(builder_).Finalize().exclusiveJoin(
      std::move(evaluation_early_stop_.promise));
}
kj::Promise<void> FrontendContext::getFileContents(
    GetFileContentsContext context) {
  auto hash = file_info_.at(context.getParams().getFile().getId()).hash;
  return util::File::HandleRequestFile(hash, context.getParams().getReceiver());
}
kj::Promise<void> FrontendContext::stopEvaluation(
    StopEvaluationContext context) {
  evaluation_early_stop_.fulfiller->fulfill();
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

kj::Promise<void> Server::requestFile(RequestFileContext context) {
  return util::File::HandleRequestFile(context);
}

}  // namespace server
