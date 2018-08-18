#include "server/server.hpp"
#include "util/file.hpp"

#include <kj/debug.h>

#include <string>

namespace server {
namespace {
uint32_t AddFileInfo(uint32_t& last_file_id,
                     std::unordered_map<uint32_t, detail::FileInfo>& info,
                     bool executable, const std::string& description) {
  uint32_t id = last_file_id++;
  info[id].id = id;
  info[id].description = description;
  info[id].executable = executable;
  return id;
}
}  // namespace

kj::Promise<void> File::getId(GetIdContext context) {
  context.getResults().setId(id_);
  return kj::READY_NOW;
}

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
  return context.getParams().getFile().getIdRequest().send().then(
      [this, context](auto res) mutable {
        KJ_LOG(INFO, "Execution " + description_,
               kj::str("Setting exacutable to ", context.getParams().getName(),
                       " id ", res.getId()));
        executable_ = res.getId();
        request_.getExecutable().getLocalFile().setName(
            context.getParams().getName());
      });
}
kj::Promise<void> Execution::setStdin(SetStdinContext context) {
  return context.getParams().getFile().getIdRequest().send().then(
      [this](auto res) mutable {
        KJ_LOG(INFO, "Execution " + description_,
               "Setting stdin file with id " + std::to_string(res.getId()));
        stdin_ = res.getId();
      });
}
kj::Promise<void> Execution::addInput(AddInputContext context) {
  return context.getParams().getFile().getIdRequest().send().then(
      [this, context](auto res) mutable {
        KJ_LOG(INFO, "Execution " + description_,
               ": Adding file with id " + std::to_string(res.getId()) +
                   " as input " + std::string(context.getParams().getName()));
        inputs_.emplace(context.getParams().getName(), res.getId());
      });
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
  stdout_ =
      AddFileInfo(frontend_context_.last_file_id_, frontend_context_.file_info_,
                  context.getParams().getIsExecutable(),
                  "Standard output of execution " + description_);
  context.getResults().setFile(kj::heap<File>(stdout_));
  KJ_LOG(INFO, "Execution " + description_,
         "Creating stdout file with id " + std::to_string(stdout_));
  return kj::READY_NOW;
}
kj::Promise<void> Execution::stderr(StderrContext context) {
  stderr_ =
      AddFileInfo(frontend_context_.last_file_id_, frontend_context_.file_info_,
                  context.getParams().getIsExecutable(),
                  "Standard error of execution " + description_);
  context.getResults().setFile(kj::heap<File>(stderr_));
  KJ_LOG(INFO, "Execution " + description_,
         "Creating stderr file with id " + std::to_string(stderr_));
  return kj::READY_NOW;
}
kj::Promise<void> Execution::output(OutputContext context) {
  uint32_t id =
      AddFileInfo(frontend_context_.last_file_id_, frontend_context_.file_info_,
                  context.getParams().getIsExecutable(),
                  "Output " + std::string(context.getParams().getName()) +
                      " of execution " + description_);
  context.getResults().setFile(kj::heap<File>(id));
  KJ_LOG(INFO, "Execution " + description_,
         kj::str("Creating output file ", context.getParams().getName(),
                 " with id ", id));
  outputs_.emplace(context.getParams().getName(), id);
  return kj::READY_NOW;
}
kj::Promise<void> Execution::notifyStart(NotifyStartContext context) {
  KJ_LOG(INFO, "Execution " + description_, "Waiting for start");
  return forked_start_.addBranch().then(
      [this]() { KJ_LOG(INFO, "Execution ", description_, ": Started"); });
}
kj::Promise<void> Execution::getResult(GetResultContext context) {
  KJ_LOG(INFO, "Execution " + description_, "Creating dependency edges");
  util::UnionPromiseBuilder dependencies;
  auto add_dep = [&dependencies, this](uint32_t id) {
    dependencies.AddPromise(
        frontend_context_.file_info_[id].forked_promise.addBranch());
  };
  if (executable_) add_dep(executable_);
  if (stdin_) add_dep(stdin_);
  for (auto& input : inputs_) {
    add_dep(input.second);
  }
  dependencies.AddPromise(
      frontend_context_.forked_evaluation_start_.addBranch());
  frontend_context_.builder_.AddPromise(std::move(finish_promise_.promise));
  return std::move(dependencies).Finalize().then([this, context]() mutable {
    KJ_LOG(INFO, "Execution " + description_, "Dependencies ready");
    auto get_hash = [this](uint32_t id, capnproto::SHA256::Builder builder) {
      frontend_context_.file_info_[id].hash.ToCapnp(builder);
    };
    get_hash(stdin_, request_.initStdin());
    if (executable_) {
      get_hash(executable_, request_.getExecutable().getLocalFile().initHash());
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
    // TODO: cache
    return frontend_context_.dispatcher_
        .AddRequest(request_, std::move(start_.fulfiller))
        .then([this, context](capnproto::Result::Reader result) mutable {
          KJ_LOG(INFO, "Execution " + description_, "Execution done");
          context.getResults().setResult(result);
          finish_promise_.fulfiller->fulfill();
          if (result.getStatus().isInternalError()) return;
          auto set_hash = [this](uint32_t id, const util::SHA256_t& hash) {
            frontend_context_.file_info_[id].hash = hash;
            frontend_context_.file_info_[id].promise.fulfiller->fulfill();
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
        });
  });
}

kj::Promise<void> FrontendContext::provideFile(ProvideFileContext context) {
  uint32_t id = AddFileInfo(last_file_id_, file_info_,
                            context.getParams().getIsExecutable(),
                            context.getParams().getDescription());
  context.getResults().setFile(kj::heap<File>(id));
  KJ_LOG(INFO, "Generating file with id " + std::to_string(id),
         context.getParams().getDescription());
  file_info_[id].provided = true;
  file_info_[id].hash = context.getParams().getHash();
  return kj::READY_NOW;
}
kj::Promise<void> FrontendContext::addExecution(AddExecutionContext context) {
  KJ_LOG(INFO, "Adding execution", context.getParams().getDescription());
  // TODO: see Server::registerFrontend
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
      builder_.AddPromise(
          util::File::MaybeGet(file.second.hash,
                               context.getParams().getSender())
              .eagerlyEvaluate(nullptr)
              .then([id = file.first,
                     fulfiller =
                         std::move(file.second.promise.fulfiller)]() mutable {
                KJ_LOG(INFO, "Received file with id " + std::to_string(id));
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
  return context.getParams().getFile().getIdRequest().send().then(
      [this, context](auto res) mutable {
        uint32_t id = res.getId();
        KJ_LOG(INFO, "Requested file with id " + std::to_string(id));
        return file_info_.at(id).forked_promise.addBranch().then(
            [id, context, this]() mutable {
              auto hash = file_info_.at(id).hash;
              return util::File::HandleRequestFile(
                         hash, context.getParams().getReceiver())
                  .then([id]() {
                    KJ_LOG(INFO, "Sent file with id " + std::to_string(id));
                  });
            });
      });
}
kj::Promise<void> FrontendContext::stopEvaluation(
    StopEvaluationContext context) {
  KJ_LOG(INFO, "Early stop");
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
