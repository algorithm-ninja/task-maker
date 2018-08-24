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
  KJ_LOG(INFO, "Execution " + description_,
         "Setting exacutable path to " +
             std::string(context.getParams().getPath()));
  request_.getExecutable().setAbsolutePath(context.getParams().getPath());
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
kj::Promise<void> Execution::disableCache(DisableCacheContext context) {
  KJ_LOG(INFO, "Execution " + description_, "Disabling cache");
  cache_enabled_ = false;
  return kj::READY_NOW;
}
kj::Promise<void> Execution::makeExclusive(MakeExclusiveContext context) {
  KJ_LOG(INFO, "Execution " + description_, "Exclusive mode");
  request_.setExclusive(true);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::setLimits(SetLimitsContext context) {
  KJ_LOG(INFO, "Execution " + description_,
         kj::str("Setting limits to ",
                 context.getParams().getLimits().toString().flatten()));
  request_.setLimits(context.getParams().getLimits());
  return kj::READY_NOW;
}
kj::Promise<void> Execution::stdout(StdoutContext context) {
  stdout_ = AddFileInfo(
      frontend_context_.last_file_id_, frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Standard output of execution " + description_);
  KJ_LOG(INFO, "Execution " + description_,
         "Creating stdout file with id " + std::to_string(stdout_));
  return kj::READY_NOW;
}
kj::Promise<void> Execution::stderr(StderrContext context) {
  stderr_ = AddFileInfo(
      frontend_context_.last_file_id_, frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Standard error of execution " + description_);
  KJ_LOG(INFO, "Execution " + description_,
         "Creating stderr file with id " + std::to_string(stderr_));
  return kj::READY_NOW;
}
kj::Promise<void> Execution::output(OutputContext context) {
  uint32_t id = AddFileInfo(
      frontend_context_.last_file_id_, frontend_context_.file_info_,
      context.getResults().initFile(), context.getParams().getIsExecutable(),
      "Output " + std::string(context.getParams().getName()) +
          " of execution " + description_);
  auto log = kj::str("Creating output file ", context.getParams().getName(),
                     " with id ", id);
  KJ_LOG(INFO, "Execution " + description_, log);
  outputs_.emplace(context.getParams().getName(), id);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::notifyStart(NotifyStartContext context) {
  KJ_LOG(INFO, "Execution " + description_, "Waiting for start");
  return forked_start_.addBranch().then(
      [this]() { KJ_LOG(INFO, "Execution " + description_, "Started"); });
}
kj::Promise<void> Execution::getResult(GetResultContext context) {
  KJ_LOG(INFO, "Execution " + description_, "Creating dependency edges");
  util::UnionPromiseBuilder dependencies;
  auto add_dep = [&dependencies, this](uint32_t id) {
    dependencies.AddPromise(
        frontend_context_.file_info_[id].forked_promise.addBranch(),
        description_ + " dep to " + std::to_string(id));
  };
  if (executable_) add_dep(executable_);
  if (stdin_) add_dep(stdin_);
  for (auto& input : inputs_) {
    add_dep(input.second);
  }
  dependencies.AddPromise(
      frontend_context_.forked_evaluation_start_.addBranch(),
      description_ + " evaluation start");
  frontend_context_.builder_.AddPromise(std::move(finish_promise_.promise),
                                        description_ + " finish_promise_");
  frontend_context_.scheduled_tasks_++;
  return std::move(dependencies)
      .Finalize()
      .then(
          [this]() {
            KJ_LOG(INFO, "Execution " + description_, "Dependencies ready");
            frontend_context_.ready_tasks_++;
          },
          [this](kj::Exception exc) {
            // Dependencies setup failed. Remove the scheduled task
            KJ_LOG(INFO, "Execution " + description_, "Dependencies failed");
            frontend_context_.scheduled_tasks_--;
            return exc;
          })
      .eagerlyEvaluate(nullptr)
      .then(
          [this, context]() mutable {
            auto get_hash = [this](uint32_t id,
                                   capnproto::SHA256::Builder builder) {
              auto hash = frontend_context_.file_info_[id].hash;
              KJ_ASSERT(!hash.isZero(), id);
              hash.ToCapnp(builder);
            };
            if (stdin_) {
              get_hash(stdin_, request_.initStdin());
            }
            if (executable_) {
              get_hash(executable_,
                       request_.getExecutable().getLocalFile().initHash());
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
            KJ_LOG(INFO, "Execution " + description_, request_);
            auto process_result = [this, context](capnproto::Result::Reader
                                                      result) mutable {
              KJ_LOG(INFO, "Execution " + description_, "Execution done");
              KJ_LOG(INFO, "Execution " + description_, result);
              KJ_ASSERT(!result.getStatus().isInternalError(),
                        result.getStatus().getInternalError());
              if (cache_enabled_) {
                frontend_context_.cache_manager_.Set(request_, result);
              }
              context.getResults().setResult(result);
              util::UnionPromiseBuilder builder;
              auto set_hash = [this, &builder, &result](
                                  uint32_t id, const util::SHA256_t& hash) {
                frontend_context_.file_info_[id].hash = hash;
                if (!result.getStatus().isSuccess()) {
                  KJ_LOG(INFO, "Marking file as failed", id, description_);
                  frontend_context_.file_info_[id].promise.fulfiller->reject(
                      KJ_EXCEPTION(FAILED, "File generation failed caused by " +
                                               description_));
                } else {
                  frontend_context_.file_info_[id].promise.fulfiller->fulfill();
                  builder.AddPromise(
                      frontend_context_.file_info_[id]
                          .forked_promise.addBranch(),
                      description_ + " output " + std::to_string(id));
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
              for (auto f : outputs_) {
                auto& ff =
                    frontend_context_.file_info_[f.second].promise.fulfiller;
                if (ff) ff->reject(KJ_EXCEPTION(FAILED, "Missing file"));
              }
              // Wait for all the outputs to be processed, then run a
              // "number of ready tasks" check.
              return std::move(builder)
                  .Finalize()
                  .then([this]() {
                    frontend_context_.ready_tasks_--;
                    frontend_context_.scheduled_tasks_--;
                    if (!frontend_context_.ready_tasks_ &&
                        frontend_context_.scheduled_tasks_) {
                      KJ_LOG(WARNING, "Execution stalled",
                             frontend_context_.ready_tasks_,
                             frontend_context_.scheduled_tasks_);
                      frontend_context_.evaluation_early_stop_.fulfiller
                          ->reject(KJ_EXCEPTION(FAILED, "Execution stalled!"));
                    } else {
                      KJ_LOG(INFO, "Finished execution", description_);
                      finish_promise_.fulfiller->fulfill();
                    }
                  })
                  .eagerlyEvaluate(nullptr);
            };

            if (cache_enabled_ &&
                frontend_context_.cache_manager_.Has(request_)) {
              start_.fulfiller->fulfill();
              // Workaround for a scheduling issue: if we run process_result
              // here, the eventloop may not have finished marking as ready the
              // executions that actually are ready before calling our stall
              // check. TODO: fix this for real.
              return kj::Promise<void>(kj::READY_NOW)
                  .then([this, process_result]() mutable {
                    return process_result(
                        frontend_context_.cache_manager_.Get(request_));
                  });
            }

            return frontend_context_.dispatcher_
                .AddRequest(request_, std::move(start_.fulfiller))
                .then(
                    [process_result](
                        capnp::Response<capnproto::Evaluator::EvaluateResults>
                            results) mutable {
                      return process_result(results.getResult());
                    },
                    [this](kj::Exception exc) {
                      finish_promise_.fulfiller->reject(kj::cp(exc));
                      kj::throwRecoverableException(std::move(exc));
                    })
                .eagerlyEvaluate(nullptr);
          },
          [this](kj::Exception exc) {
            KJ_LOG(
                INFO,
                "Marking execution as failed because its dependencies failed",
                description_);
            start_.fulfiller->reject(kj::cp(exc));
            finish_promise_.fulfiller->reject(kj::cp(exc));
            auto mark_as_failed = [this](std::string name, int id) {
              KJ_LOG(INFO, description_, "Marking as failed", name, id);
              auto& ff = frontend_context_.file_info_[id].promise.fulfiller;
              if (ff)
                ff->reject(
                    KJ_EXCEPTION(FAILED, "Dependency failed: " + description_));
            };
            mark_as_failed("stdout", stdout_);
            mark_as_failed("stdout", stderr_);
            for (auto f : outputs_) {
              mark_as_failed(f.first, f.second);
            }
            kj::throwRecoverableException(std::move(exc));
          });
}

kj::Promise<void> FrontendContext::provideFile(ProvideFileContext context) {
  std::string descr = context.getParams().getDescription();
  uint32_t id =
      AddFileInfo(last_file_id_, file_info_, context.getResults().initFile(),
                  context.getParams().getIsExecutable(), descr);
  KJ_LOG(INFO, "Generating file with id " + std::to_string(id), "" + descr);
  file_info_[id].provided = true;
  file_info_[id].hash = context.getParams().getHash();
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::addExecution(AddExecutionContext context) {
  KJ_LOG(INFO, "Adding execution " +
                   std::string(context.getParams().getDescription()));
  context.getResults().setExecution(
      kj::heap<Execution>(*this, context.getParams().getDescription()));
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::startEvaluation(
    StartEvaluationContext context) {
  KJ_LOG(INFO, "Starting evaluation");
  evaluation_start_.fulfiller->fulfill();  // Starts the evaluation
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
    }
    // Wait for all files to be ready
    builder_.AddPromise(file.second.forked_promise.addBranch(),
                        "Input file " + std::to_string(file.first) + " " +
                            file.second.description);
  }
  return std::move(builder_)
      .Finalize()
      .then([]() { KJ_LOG(INFO, "Evaluation success"); },
            [](kj::Exception ex) { KJ_LOG(INFO, "Evaluation killed by", ex); })
      .exclusiveJoin(std::move(evaluation_early_stop_.promise))
      .eagerlyEvaluate(nullptr);
}
kj::Promise<void> FrontendContext::getFileContents(
    GetFileContentsContext context) {
  uint32_t id = context.getParams().getFile().getId();
  KJ_LOG(INFO, "Requested file with id " + std::to_string(id));
  kj::PromiseFulfillerPair<void> pf = kj::newPromiseAndFulfiller<void>();
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
  return file_info_[id].forked_promise.addBranch().then(
      [send_file = std::move(send_file)]() mutable { return (*send_file)(); },
      [send_file = send_file_ptr, this, id](kj::Exception exc) mutable {
        auto hash = file_info_[id].hash;
        if (hash.isZero()) {
          kj::throwRecoverableException(std::move(exc));
        }
        return (*send_file)();
      });
}
kj::Promise<void> FrontendContext::stopEvaluation(
    StopEvaluationContext context) {
  KJ_LOG(INFO, "Early stop");
  evaluation_early_stop_.fulfiller->fulfill();
  return kj::READY_NOW;
}

kj::Promise<void> Server::registerFrontend(RegisterFrontendContext context) {
  context.getResults().setContext(
      kj::heap<FrontendContext>(dispatcher_, cache_manager_));
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
