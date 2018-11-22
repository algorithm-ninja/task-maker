#include "server/server.hpp"
#include "util/file.hpp"

#include <kj/debug.h>

#include <string>

namespace server {
namespace {
uint32_t AddFileInfo(uint32_t* last_file_id,
                     std::unordered_map<uint32_t, detail::FileInfo>* info,
                     capnproto::File::Builder builder, bool executable,
                     const std::string& description) {
  uint32_t id = (*last_file_id)++;
  (*info)[id].id = id;
  (*info)[id].description = description;
  (*info)[id].executable = executable;
  builder.setId(id);
  return id;
}
}  // namespace

void ExecutionGroup::Register(Execution* ex) { executions_.push_back(ex); }

void ExecutionGroup::setExclusive() { request_.setExclusive(true); }
void ExecutionGroup::disableCache() { cache_enabled_ = false; }
kj::Promise<void> ExecutionGroup::notifyStart() {
  return forked_start_.addBranch()
      .then([this]() {
        KJ_LOG(INFO, "Execution group " + description_, "Started");
      })
      .exclusiveJoin(frontend_context_.forked_early_stop_.addBranch());
}

kj::Promise<void> ExecutionGroup::addExecution(AddExecutionContext context) {
  KJ_LOG(INFO, "Adding execution " +
                   std::string(context.getParams().getDescription()) +
                   " to group " + description_);
  context.getResults().setExecution(
      kj::heap<Execution>(&frontend_context_,
                          std::string(context.getParams().getDescription()) +
                              " of group " + description_,
                          this));
  return kj::READY_NOW;
}

kj::Promise<void> ExecutionGroup::createFifo(CreateFifoContext context) {
  KJ_LOG(INFO, "Creating FIFO " + std::to_string(next_fifo_) + " in group " +
                   description_);
  context.getResults().getFifo().setId(next_fifo_++);
  return kj::READY_NOW;
}

kj::Promise<void> ExecutionGroup::Finalize(Execution* ex) {
  if (!finalized_) {
    finalized_ = true;
    KJ_LOG(INFO, "Execution group " + description_,
           "Creating dependency edges");
    util::UnionPromiseBuilder dependencies;
    dependencies.AddPromise(
        frontend_context_.forked_evaluation_start_.addBranch(),
        description_ + " evaluation start");
    for (auto ex : executions_) {
      ex->addDependencies(&dependencies);
    }
    done_ =
        std::move(dependencies)
            .Finalize()
            .then(
                [this]() -> kj::Promise<void> {
                  request_.initProcesses(executions_.size());
                  for (size_t i = 0; i < executions_.size(); i++) {
                    executions_[i]->prepareRequest();
                    request_.getProcesses().setWithCaveats(
                        i, executions_[i]->request_);
                  }
                  KJ_LOG(INFO, "Execution group " + description_, request_);
                  return kj::READY_NOW;
                },
                [this](kj::Exception exc) -> kj::Promise<void> {
                  start_.fulfiller->reject(kj::cp(exc));
                  for (auto ex : executions_) {
                    ex->onDependenciesFailure(kj::cp(exc));
                  }
                  return kj::Promise<void>(std::move(exc));
                })
            .eagerlyEvaluate(nullptr)
            .then([this]() mutable {
              if (cache_enabled_ &&
                  frontend_context_.cache_manager_.Has(request_)) {
                auto res = frontend_context_.cache_manager_.Get(request_);
                start_.fulfiller->fulfill();
                util::UnionPromiseBuilder dependencies_propagated;
                for (size_t i = 0; i < executions_.size(); i++) {
                  executions_[i]->processResult(res.getProcesses()[i],
                                                &dependencies_propagated, true);
                }
                return std::move(dependencies_propagated)
                    .Finalize()
                    .then([this]() {
                      for (auto ex : executions_) {
                        ex->onDependenciesPropagated();
                      }
                    })
                    .eagerlyEvaluate(nullptr);
              }

              return frontend_context_.dispatcher_
                  .AddRequest(request_, std::move(start_.fulfiller),
                              frontend_context_.canceled_)
                  .then(
                      [this](
                          capnp::Response<capnproto::Evaluator::EvaluateResults>
                              results) mutable {
                        auto res = results.getResult();
                        util::UnionPromiseBuilder dependencies_propagated;
                        if (cache_enabled_) {
                          frontend_context_.cache_manager_.Set(request_, res);
                        }
                        for (size_t i = 0; i < executions_.size(); i++) {
                          executions_[i]->processResult(
                              res.getProcesses()[i], &dependencies_propagated);
                        }
                        return std::move(dependencies_propagated)
                            .Finalize()
                            .then([this]() {
                              for (auto ex : executions_) {
                                ex->onDependenciesPropagated();
                              }
                            })
                            .eagerlyEvaluate(nullptr);
                      },
                      [this](kj::Exception exc) {
                        for (auto ex : executions_) {
                          ex->finish_promise_.fulfiller->reject(kj::cp(exc));
                        }
                        return kj::Promise<void>(std::move(exc));
                      })
                  .eagerlyEvaluate(nullptr);
            })
            .exclusiveJoin(frontend_context_.forked_early_stop_.addBranch())
            .eagerlyEvaluate(nullptr);
    forked_done_ = done_.fork();
  }
  for (const auto& execution : executions_) {
    if (execution == ex) {
      return forked_done_.addBranch();
    }
  }
  KJ_FAIL_ASSERT("Invalid execution for this group!");
}  // namespace server

Execution::Execution(FrontendContext* frontend_context, std::string description,
                     ExecutionGroup* group)
    : frontend_context_(*frontend_context),
      description_(std::move(description)),
      group_(*group) {
  group_.Register(this);
}

kj::Promise<void> Execution::setExecutablePath(
    SetExecutablePathContext context) {
  KJ_LOG(INFO, "Execution " + description_,
         "Setting exacutable path to " +
             std::string(context.getParams().getPath()));
  request_.getExecutable().setSystem(context.getParams().getPath());
  executable_ = 0;
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setExecutable(SetExecutableContext context) {
  auto log = kj::str("Setting exacutable to ", context.getParams().getName(),
                     " id ", context.getParams().getFile().getId());
  KJ_LOG(INFO, "Execution " + description_, log);
  executable_ = context.getParams().getFile().getId();
  request_.getExecutable().initLocalFile().setName(
      context.getParams().getName());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setStdin(SetStdinContext context) {
  KJ_ASSERT(!stdin_ && !stdin_fifo_);
  KJ_LOG(INFO, "Execution " + description_,
         "Setting stdin file with id " +
             std::to_string(context.getParams().getFile().getId()));
  stdin_ = context.getParams().getFile().getId();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::addInput(AddInputContext context) {
  KJ_LOG(INFO, "Execution " + description_,
         "Adding file with id " +
             std::to_string(context.getParams().getFile().getId()) +
             " as input " + std::string(context.getParams().getName()));
  inputs_.emplace(context.getParams().getName(),
                  context.getParams().getFile().getId());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setArgs(SetArgsContext context) {
  std::string args;
  for (auto s : context.getParams().getArgs()) args += " " + std::string(s);
  KJ_LOG(INFO, "Execution " + description_, "Setting args to" + args);
  request_.setArgs(context.getParams().getArgs());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::disableCache(DisableCacheContext /*context*/) {
  KJ_LOG(INFO, "Execution " + description_, "Disabling cache");
  group_.disableCache();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::makeExclusive(MakeExclusiveContext /*context*/) {
  KJ_LOG(INFO, "Execution " + description_, "Exclusive mode");
  group_.setExclusive();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setLimits(SetLimitsContext context) {
  KJ_LOG(INFO, "Execution " + description_,
         kj::str("Setting limits to ",
                 context.getParams().getLimits().toString().flatten()));
  request_.setLimits(context.getParams().getLimits());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setExtraTime(SetExtraTimeContext context) {
  KJ_LOG(INFO, "Execution " + description_,
         kj::str("Setting extra time to ",
                 std::to_string(context.getParams().getExtraTime())));
  request_.setExtraTime(context.getParams().getExtraTime());
  return kj::READY_NOW;
}
// TODO: check that this FIFO is from the correct execution group
kj::Promise<void> Execution::addFifo(AddFifoContext context) {
  KJ_LOG(INFO, "Execution " + description_,
         "Adding FIFO with id " +
             std::to_string(context.getParams().getFifo().getId()) + " as " +
             std::string(context.getParams().getName()));
  fifos_.emplace(context.getParams().getName(),
                 context.getParams().getFifo().getId());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setStdinFifo(SetStdinFifoContext context) {
  KJ_ASSERT(!stdin_ && !stdin_fifo_);
  KJ_LOG(INFO, "Execution " + description_,
         "Adding FIFO with id " +
             std::to_string(context.getParams().getFifo().getId()) +
             " as stdin");
  stdin_fifo_ = context.getParams().getFifo().getId();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setStdoutFifo(SetStdoutFifoContext context) {
  KJ_ASSERT(!stdout_ && !stdout_fifo_);
  KJ_LOG(INFO, "Execution " + description_,
         "Addoutg FIFO with id " +
             std::to_string(context.getParams().getFifo().getId()) +
             " as stdout");
  stdout_fifo_ = context.getParams().getFifo().getId();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setStderrFifo(SetStderrFifoContext context) {
  KJ_ASSERT(!stderr_ && !stderr_fifo_);
  KJ_LOG(INFO, "Execution " + description_,
         "Adderrg FIFO with id " +
             std::to_string(context.getParams().getFifo().getId()) +
             " as stderr");
  stderr_fifo_ = context.getParams().getFifo().getId();
  return kj::READY_NOW;
}
kj::Promise<void> Execution::getStdout(GetStdoutContext context) {
  KJ_ASSERT(!stdout_ && !stdout_fifo_);
  stdout_ = AddFileInfo(
      &frontend_context_.last_file_id_, &frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Standard output of execution " + description_);
  KJ_LOG(INFO, "Execution " + description_,
         "Creating stdout file with id " + std::to_string(stdout_));
  return kj::READY_NOW;
}
kj::Promise<void> Execution::getStderr(GetStderrContext context) {
  KJ_ASSERT(!stderr_ && !stderr_fifo_);
  stderr_ = AddFileInfo(
      &frontend_context_.last_file_id_, &frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Standard error of execution " + description_);
  KJ_LOG(INFO, "Execution " + description_,
         "Creating stderr file with id " + std::to_string(stderr_));
  return kj::READY_NOW;
}
kj::Promise<void> Execution::getOutput(GetOutputContext context) {
  uint32_t id = AddFileInfo(
      &frontend_context_.last_file_id_, &frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Output " + std::string(context.getParams().getName()) +
          " of execution " + description_);
  auto log = kj::str("Creating output file ", context.getParams().getName(),
                     " with id ", id);
  KJ_LOG(INFO, "Execution " + description_, log);
  outputs_.emplace(context.getParams().getName(), id);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::notifyStart(NotifyStartContext /*context*/) {
  KJ_LOG(INFO, "Execution " + description_, "Waiting for start");
  return group_.notifyStart();
}

void Execution::addDependencies(util::UnionPromiseBuilder* dependencies) {
  auto add_dep = [&dependencies, this](uint32_t id) {
    KJ_ASSERT(id != 0);
    frontend_context_.file_info_[id].dependencies_propagated_.AddPromise(
        dependencies->AddPromise(
            frontend_context_.file_info_[id].forked_promise.addBranch(),
            description_ + " dep to " + std::to_string(id)));
  };
  if (executable_) add_dep(executable_);
  if (stdin_) add_dep(stdin_);
  for (auto& input : inputs_) {
    add_dep(input.second);
  }
  dependencies->OnReady([this]() {
    KJ_LOG(INFO, "Execution " + description_, "Dependencies ready");
    frontend_context_.ready_tasks_++;
  });
  dependencies->OnFailure([this](kj::Exception exc) {
    // Dependencies setup failed. Remove the scheduled task
    KJ_LOG(INFO, "Execution " + description_, "Dependencies failed");
    frontend_context_.scheduled_tasks_--;
  });
}

void Execution::prepareRequest() {
  auto get_hash = [this](uint32_t id, capnproto::SHA256::Builder builder) {
    KJ_ASSERT(id != 0);
    auto hash = frontend_context_.file_info_[id].hash;
    KJ_ASSERT(!hash.isZero(), id);
    hash.ToCapnp(builder);
  };
  if (stdin_) {
    get_hash(stdin_, request_.initStdin().initHash());
  } else if (stdin_fifo_) {
    request_.initStdin().setFifo(stdin_fifo_);
  }
  if (stdout_fifo_) {
    request_.setStdout(stdout_fifo_);
  }
  if (stderr_fifo_) {
    request_.setStderr(stderr_fifo_);
  }
  if (executable_) {
    get_hash(executable_, request_.getExecutable().getLocalFile().initHash());
  }
  request_.initFifos(fifos_.size());
  {
    size_t i = 0;
    for (auto& fifo : fifos_) {
      request_.getFifos()[i].setName(fifo.first);
      request_.getFifos()[i].setId(fifo.second);
      i++;
    }
  }
  request_.initInputFiles(inputs_.size());
  {
    size_t i = 0;
    for (auto& input : inputs_) {
      request_.getInputFiles()[i].setName(input.first);
      get_hash(input.second, request_.getInputFiles()[i].getHash());
      i++;
    }
  }
  request_.initOutputFiles(outputs_.size());
  {
    size_t i = 0;
    for (auto& output : outputs_) {
      request_.getOutputFiles().set(i, output.first);
      i++;
    }
  }
}

void Execution::processResult(
    capnproto::ProcessResult::Reader result,
    util::UnionPromiseBuilder* dependencies_propagated, bool from_cache) {
  KJ_IF_MAYBE(ctx, context_) {
    ctx->getResults().setResult(result);
    ctx->getResults().getResult().setWasCached(from_cache);
  }
  KJ_LOG(INFO, "Execution " + description_, result);
  if (result.getStatus().isInternalError()) {
    frontend_context_.evaluation_early_stop_.fulfiller->reject(
        KJ_EXCEPTION(FAILED, result.getStatus().getInternalError()));
    KJ_FAIL_ASSERT(result.getStatus().getInternalError());
  }
  auto set_hash = [this, &result](uint32_t id, const util::SHA256_t& hash) {
    KJ_ASSERT(id != 0);
    frontend_context_.file_info_[id].hash = hash;
    if (!result.getStatus().isSuccess()) {
      KJ_LOG(INFO, "Marking file as failed", id, description_);
      frontend_context_.file_info_[id].promise.fulfiller->reject(KJ_EXCEPTION(
          FAILED, "File generation failed caused by " + description_));
    } else {
      frontend_context_.file_info_[id].promise.fulfiller->fulfill();
    }
  };
  if (stdout_) {
    set_hash(stdout_, result.getStdout());
  }
  if (stderr_) {
    set_hash(stderr_, result.getStderr());
  }
  for (auto output : result.getOutputFiles()) {
    std::string name = output.getName();
    KJ_REQUIRE(outputs_.count(output.getName()), output.getName(),
               "Unexpected output!");
    set_hash(outputs_[output.getName()], output.getHash());
  }
  // Reject all the non-fulfilled promises.
  util::UnionPromiseBuilder builder;
  for (const auto& f : outputs_) {
    auto& ff = frontend_context_.file_info_[f.second].promise.fulfiller;
    if (ff) {
      ff->reject(KJ_EXCEPTION(FAILED, "Missing file"));
    }
    dependencies_propagated->AddPromise(
        std::move(
            frontend_context_.file_info_[f.second].dependencies_propagated_)
            .Finalize());
  }
}

void Execution::onDependenciesPropagated() {
  frontend_context_.ready_tasks_--;
  frontend_context_.scheduled_tasks_--;
  if (!frontend_context_.ready_tasks_ && frontend_context_.scheduled_tasks_) {
    KJ_LOG(WARNING, "Execution stalled", frontend_context_.ready_tasks_,
           frontend_context_.scheduled_tasks_);
    frontend_context_.evaluation_early_stop_.fulfiller->reject(
        KJ_EXCEPTION(FAILED, "Execution stalled!"));
  } else {
    KJ_LOG(INFO, "Finished execution", description_);
    finish_promise_.fulfiller->fulfill();
  }
}

void Execution::onDependenciesFailure(kj::Exception exc) {
  KJ_LOG(INFO, "Marking execution as failed because its dependencies failed",
         description_);
  finish_promise_.fulfiller->reject(kj::cp(exc));
  auto mark_as_failed = [this](std::string name, int id) {
    KJ_LOG(INFO, description_, "Marking as failed", name, id);
    KJ_ASSERT(id != 0);
    auto& ff = frontend_context_.file_info_[id].promise.fulfiller;
    if (ff) {
      ff->reject(KJ_EXCEPTION(FAILED, "Dependency failed: " + description_));
    }
  };
  if (stdout_) mark_as_failed("stdout", stdout_);
  if (stderr_) mark_as_failed("stdout", stderr_);
  for (const auto& f : outputs_) {
    mark_as_failed(f.first, f.second);
  }
}

kj::Promise<void> Execution::getResult(GetResultContext context) {
  context_ = context;
  frontend_context_.scheduled_tasks_++;
  frontend_context_.builder_.AddPromise(std::move(finish_promise_.promise),
                                        description_ + " finish_promise_");
  return group_.Finalize(this).exclusiveJoin(
      frontend_context_.forked_early_stop_.addBranch());
}

kj::Promise<void> FrontendContext::provideFile(ProvideFileContext context) {
  std::string descr = context.getParams().getDescription();
  uint32_t id =
      AddFileInfo(&last_file_id_, &file_info_, context.getResults().initFile(),
                  context.getParams().getIsExecutable(), descr);
  KJ_LOG(INFO, "Generating file with id " + std::to_string(id), "" + descr);
  KJ_ASSERT(id != 0);
  file_info_[id].provided = true;
  file_info_[id].hash = context.getParams().getHash();
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::addExecution(AddExecutionContext context) {
  KJ_LOG(INFO, "Adding execution " +
                   std::string(context.getParams().getDescription()));
  groups_.push_back(
      kj::heap<ExecutionGroup>(this, context.getParams().getDescription()));
  context.getResults().setExecution(kj::heap<Execution>(
      this, context.getParams().getDescription(), groups_.back()));
  return kj::READY_NOW;
}

kj::Promise<void> FrontendContext::addExecutionGroup(
    AddExecutionGroupContext context) {
  KJ_LOG(INFO, "Adding execution group " +
                   std::string(context.getParams().getDescription()));
  context.getResults().setGroup(
      kj::heap<ExecutionGroup>(this, context.getParams().getDescription()));
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::startEvaluation(
    StartEvaluationContext context) {
  KJ_LOG(INFO, "Starting evaluation");
  util::UnionPromiseBuilder provided_files_ready_;
  for (auto& file : file_info_) {
    if (file.second.provided) {
      auto ff = file.second.promise.fulfiller.get();
      builder_.AddPromise(
          util::File::MaybeGet(file.second.hash,
                               context.getParams().getSender())
              .then(
                  [id = file.first,
                   fulfiller =
                       std::move(file.second.promise.fulfiller)]() mutable {
                    KJ_LOG(INFO, "Received file with id " + std::to_string(id));
                    fulfiller->fulfill();
                  },
                  [fulfiller = ff](kj::Exception exc) {
                    fulfiller->reject(kj::cp(exc));
                    return exc;
                  })
              .eagerlyEvaluate(nullptr),
          "MaybeGet file " + std::to_string(file.first) + " " +
              file.second.description);
      // Only mark a file as ready when all of its dependencies have been
      // propagated.
      provided_files_ready_.AddPromise(
          std::move(file.second.dependencies_propagated_).Finalize());
    }
    // Wait for all files to be ready
    builder_.AddPromise(file.second.forked_promise.addBranch(),
                        "Input file " + std::to_string(file.first) + " " +
                            file.second.description);
  }
  // When the input files are done, start the evaluation.
  builder_.AddPromise(
      std::move(provided_files_ready_)
          .Finalize()
          .then([this]() { evaluation_start_.fulfiller->fulfill(); },
                [this](kj::Exception exc) {
                  evaluation_start_.fulfiller->reject(kj::cp(exc));
                }));
  return std::move(builder_)
      .Finalize()
      .then([]() { KJ_LOG(INFO, "Evaluation success"); },
            [](kj::Exception ex) { KJ_LOG(INFO, "Evaluation killed by", ex); })
      .exclusiveJoin(forked_early_stop_.addBranch())
      .eagerlyEvaluate(nullptr);
}
kj::Promise<void> FrontendContext::getFileContents(
    GetFileContentsContext context) {
  uint32_t id = context.getParams().getFile().getId();
  KJ_LOG(INFO, "Requested file with id " + std::to_string(id));
  kj::PromiseFulfillerPair<void> pf = kj::newPromiseAndFulfiller<void>();
  builder_.AddPromise(std::move(pf.promise));
  auto send_file = kj::heap<kj::Function<kj::Promise<void>()>>(
      [id, context, this, fulfiller = std::move(pf.fulfiller)]() mutable {
        auto hash = file_info_.at(id).hash;
        KJ_LOG(INFO, "Sending file with id " + std::to_string(id), hash.Hex());
        auto ff = fulfiller.get();
        return util::File::HandleRequestFile(hash,
                                             context.getParams().getReceiver())
            .then(
                [id, fulfiller = std::move(fulfiller)]() mutable {
                  fulfiller->fulfill();
                  KJ_LOG(INFO, "Sent file with id " + std::to_string(id));
                },
                [ff](kj::Exception exc) {
                  ff->reject(kj::cp(exc));
                  return exc;
                });
      });
  auto send_file_ptr = send_file.get();
  KJ_ASSERT(id != 0);
  return file_info_[id]
      .forked_promise.addBranch()
      .then([send_file =
                 std::move(send_file)]() mutable { return (*send_file)(); },
            [send_file = send_file_ptr, this, id](kj::Exception exc) mutable {
              KJ_ASSERT(id != 0);
              auto hash = file_info_[id].hash;
              if (hash.isZero()) {
                kj::throwRecoverableException(std::move(exc));
              }
              return (*send_file)();
            })
      .exclusiveJoin(forked_early_stop_.addBranch());
}
kj::Promise<void> FrontendContext::stopEvaluation(
    StopEvaluationContext /*context*/) {
  KJ_LOG(INFO, "Early stop");
  *canceled_ = true;
  evaluation_early_stop_.fulfiller->reject(
      KJ_EXCEPTION(FAILED, "Evaluation stopped"));
  return kj::READY_NOW;
}

kj::Promise<void> Server::registerFrontend(RegisterFrontendContext context) {
  context.getResults().setContext(
      kj::heap<FrontendContext>(&dispatcher_, &cache_manager_));
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
