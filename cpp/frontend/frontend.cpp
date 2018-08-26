#include "frontend/frontend.hpp"
#include "util/file.hpp"

namespace frontend {
namespace {
class FileProvider : public capnproto::FileSender::Server {
 public:
  FileProvider(std::unordered_map<util::SHA256_t, std::string,
                                  util::SHA256_t::Hasher>& known_files)
      : known_files_(known_files) {}

  kj::Promise<void> requestFile(RequestFileContext context) {
    std::string path = known_files_.at(context.getParams().getHash());
    return util::File::HandleRequestFile(path,
                                         context.getParams().getReceiver());
  }

 private:
  std::unordered_map<util::SHA256_t, std::string, util::SHA256_t::Hasher>
      known_files_;
};

}  // namespace

void File::getContentsAsString(
    std::function<void(const std::string&)> callback) {
  auto pf = kj::newPromiseAndFulfiller<void>();
  frontend_.builder_.AddPromise(std::move(pf.promise));
  frontend_.finish_builder_.AddPromise(
      forked_promise.addBranch().then(
          [this, callback,
           fulfiller = std::move(pf.fulfiller)](auto file) mutable {
            auto req = frontend_.frontend_context_.getFileContentsRequest();
            auto output = kj::heap<std::string>();
            auto output_ptr = output.get();
            req.setFile(file);
            req.setReceiver(kj::heap<util::File::Receiver>(
                [output = std::move(output)](util::File::Chunk data) mutable {
                  *output += std::string(data.asChars().begin(), data.size());
                }));
            kj::Promise<void> ret = req.send().ignoreResult().then(
                [output_ptr, callback]() { callback(*output_ptr); });
            fulfiller->fulfill();
            return std::move(ret);
          }),
      "Get file");
}

void File::getContentsToFile(const std::string& path, bool overwrite,
                             bool exist_ok) {
  auto pf = kj::newPromiseAndFulfiller<void>();
  frontend_.builder_.AddPromise(std::move(pf.promise));
  frontend_.finish_builder_.AddPromise(
      forked_promise.addBranch().then([this, path, exist_ok, overwrite,
                                       fulfiller = std::move(pf.fulfiller)](
                                          auto file) mutable {
        auto req = frontend_.frontend_context_.getFileContentsRequest();
        req.setFile(file);
        req.setReceiver(kj::heap<util::File::Receiver>(
            util::File::LazyChunkReceiver([path, overwrite, exist_ok]() {
              return util::File::Write(path, overwrite, exist_ok);
            })));
        kj::Promise<void> ret = req.send().ignoreResult().then([this, path]() {
          if (is_executable_) {
            util::File::MakeExecutable(path);
          }
        });
        fulfiller->fulfill();
        return ret;
      }),
      "Get file");
}

Frontend::Frontend(std::string server, int port)
    : client_(server, port),
      frontend_context_(
          client_.getMain<capnproto::MainServer>()
              .registerFrontendRequest()
              .send()
              .then([](auto res) { return res.getContext(); },
                    [](auto exc)
                        -> kj::Promise<capnproto::FrontendContext::Client> {
                      kj::throwRecoverableException(kj::cp(exc));
                      return std::move(exc);
                    })
              .wait(client_.getWaitScope())),
      finish_builder_(false),
      stop_request_(kj::READY_NOW) {}

File* Frontend::provideFile(const std::string& path,
                            const std::string& description,
                            bool is_executable) {
  auto req = frontend_context_.provideFileRequest();
  util::SHA256_t hash = util::File::Hash(path);
  known_files_.emplace(hash, path);
  hash.ToCapnp(req.initHash());
  req.setDescription(description);
  req.setIsExecutable(is_executable);
  files_.push_back(File::New(req.send(), *this, is_executable));
  return files_.back().get();
}

Execution* Frontend::addExecution(const std::string& description) {
  auto req = frontend_context_.addExecutionRequest();
  req.setDescription(description);
  executions_.push_back(std::make_unique<Execution>(
      description, req.send().then([](auto r) { return r.getExecution(); }),
      files_, builder_, finish_builder_, *this));
  return executions_.back().get();
}

ExecutionGroup* Frontend::addExecutionGroup(const std::string& description) {
  auto req = frontend_context_.addExecutionGroupRequest();
  req.setDescription(description);
  groups_.push_back(std::make_unique<ExecutionGroup>(
      description, req.send().then([](auto r) { return r.getGroup(); }), files_,
      builder_, finish_builder_, *this));
  return groups_.back().get();
}

void Frontend::evaluate() {
  finish_builder_.AddPromise(std::move(builder_).Finalize().then([this]() {
    auto req = frontend_context_.startEvaluationRequest();
    req.setSender(kj::heap<FileProvider>(known_files_));
    return req.send().ignoreResult();
  }),
                             "Evaluate");
  std::move(finish_builder_).Finalize().wait(client_.getWaitScope());
  stop_request_.wait(client_.getWaitScope());
}

void Frontend::stopEvaluation() {
  stop_request_ =
      frontend_context_.stopEvaluationRequest().send().ignoreResult();
}

Execution* ExecutionGroup::addExecution(const std::string& description) {
  auto req = execution_group_.addExecutionRequest();
  req.setDescription(description);
  executions_.push_back(std::make_unique<Execution>(
      description_ + " of group " + description,
      req.send().then([](auto r) { return r.getExecution(); }), files_,
      builder_, finish_builder_, frontend_));
  return executions_.back().get();
}

Fifo* ExecutionGroup::createFifo() {
  auto req = execution_group_.createFifoRequest();
  fifos_.push_back(Fifo::New(req.send()));
  return fifos_.back().get();
}

void Execution::setExecutablePath(const std::string& path) {
  auto req = execution_.setExecutablePathRequest();
  req.setPath(path);
  my_builder_.AddPromise(req.send().ignoreResult());
}

void Execution::setExecutable(const std::string& name, File* file) {
  my_builder_.AddPromise(
      file->forked_promise.addBranch().then([this, name](auto file) {
        auto req = execution_.setExecutableRequest();
        req.setName(name);
        req.setFile(file);
        builder_.AddPromise(req.send().ignoreResult());
      }));
}

void Execution::setStdin(File* file) {
  my_builder_.AddPromise(
      file->forked_promise.addBranch().then([this](auto file) {
        auto req = execution_.setStdinRequest();
        req.setFile(file);
        builder_.AddPromise(req.send().ignoreResult());
      }));
}

void Execution::addInput(const std::string& name, File* file) {
  my_builder_.AddPromise(
      file->forked_promise.addBranch().then([this, name](auto file) {
        auto req = execution_.addInputRequest();
        req.setName(name);
        req.setFile(file);
        builder_.AddPromise(req.send().ignoreResult());
      }));
}

void Execution::addFifo(const std::string& name, Fifo* fifo) {
  my_builder_.AddPromise(
      fifo->forked_promise.addBranch().then([this, name](auto fifo) {
        auto req = execution_.addFifoRequest();
        req.setName(name);
        req.setFifo(fifo);
        builder_.AddPromise(req.send().ignoreResult());
      }));
}

void Execution::setArgs(const std::vector<std::string>& args) {
  auto req = execution_.setArgsRequest();
  req.initArgs(args.size());
  for (size_t i = 0; i < args.size(); i++) {
    req.getArgs().set(i, args[i]);
  }
  my_builder_.AddPromise(req.send().ignoreResult());
}

void Execution::disableCache() {
  my_builder_.AddPromise(
      execution_.disableCacheRequest().send().ignoreResult());
}

void Execution::makeExclusive() {
  my_builder_.AddPromise(
      execution_.makeExclusiveRequest().send().ignoreResult());
}

void Execution::setLimits(const Resources& limits) {
  auto req = execution_.setLimitsRequest();
  req.getLimits().setCpuTime(limits.cpu_time);
  req.getLimits().setWallTime(limits.wall_time);
  req.getLimits().setMemory(limits.memory);
  req.getLimits().setNproc(limits.nproc);
  req.getLimits().setNofiles(limits.nofiles);
  req.getLimits().setFsize(limits.fsize);
  req.getLimits().setMemlock(limits.memlock);
  req.getLimits().setStack(limits.stack);
  my_builder_.AddPromise(req.send().ignoreResult());
}

void Execution::setExtraTime(float extra_time) {
  auto req = execution_.setExtraTimeRequest();
  req.setExtraTime(extra_time);
  my_builder_.AddPromise(req.send().ignoreResult());
}

File* Execution::stdout(bool is_executable) {
  auto req = execution_.stdoutRequest();
  req.setIsExecutable(is_executable);
  files_.push_back(File::New(req.send(), frontend_, is_executable));
  return files_.back().get();
}

File* Execution::stderr(bool is_executable) {
  auto req = execution_.stderrRequest();
  req.setIsExecutable(is_executable);
  files_.push_back(File::New(req.send(), frontend_, is_executable));
  return files_.back().get();
}
File* Execution::output(const std::string& name, bool is_executable) {
  auto req = execution_.outputRequest();
  req.setIsExecutable(is_executable);
  req.setName(name);
  files_.push_back(File::New(req.send(), frontend_, is_executable));
  return files_.back().get();
}

void Execution::notifyStart(std::function<void()> callback) {
  finish_builder_.AddPromise(
      execution_.notifyStartRequest()
          .send()
          .ignoreResult()
          .then([callback]() { callback(); }, [](auto exc) {})
          .eagerlyEvaluate(nullptr),
      "Notify start " + description_);
}

void Execution::getResult(std::function<void(Result)> callback,
                          std::function<void()> errored) {
  auto promise = kj::newPromiseAndFulfiller<void>();
  builder_.AddPromise(std::move(promise.promise));
  auto ff = promise.fulfiller.get();
  finish_builder_.AddPromise(
      std::move(my_builder_)
          .Finalize()
          .then(
              [this, callback, errored,
               fulfiller = std::move(promise.fulfiller)]() mutable {
                fulfiller->fulfill();
                return execution_.getResultRequest()
                    .send()
                    .then(
                        [callback](auto res) {
                          auto r = res.getResult();
                          Result result;
                          result.status = r.getStatus().which();
                          if (r.getStatus().isSignal()) {
                            result.signal = r.getStatus().getSignal();
                          }
                          if (r.getStatus().isReturnCode()) {
                            result.return_code = r.getStatus().getReturnCode();
                          }
                          if (r.getStatus().isInternalError()) {
                            result.error = r.getStatus().getInternalError();
                          }
                          if (r.getStatus().isMissingExecutable()) {
                            result.error = r.getStatus().getMissingExecutable();
                          }
                          result.resources.cpu_time =
                              r.getResourceUsage().getCpuTime();
                          result.resources.sys_time =
                              r.getResourceUsage().getSysTime();
                          result.resources.wall_time =
                              r.getResourceUsage().getWallTime();
                          result.resources.memory =
                              r.getResourceUsage().getMemory();
                          result.resources.nproc =
                              r.getResourceUsage().getNproc();
                          result.resources.nofiles =
                              r.getResourceUsage().getNofiles();
                          result.resources.fsize =
                              r.getResourceUsage().getFsize();
                          result.resources.memlock =
                              r.getResourceUsage().getMemlock();
                          result.resources.stack =
                              r.getResourceUsage().getStack();
                          callback(result);
                        },
                        [errored](auto exc) {
                          if (errored) errored();
                        })
                    .eagerlyEvaluate(nullptr);
              },
              [fulfiller = ff](kj::Exception exc) {
                fulfiller->reject(std::move(exc));
              }),
      "Get result " + description_);
}
}  // namespace frontend
