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

Frontend::Frontend(std::string server, int port)
    : client_(server, port),
      frontend_context_(client_.getMain<capnproto::MainServer>()
                            .registerFrontendRequest()
                            .send()
                            .then([](auto res) { return res.getContext(); })) {}
File Frontend::provideFile(const std::string& path,
                           const std::string& description, bool is_executable) {
  auto req = frontend_context_.provideFileRequest();
  util::SHA256_t hash = util::File::Hash(path);
  known_files_.emplace(hash, path);
  hash.ToCapnp(req.initHash());
  req.setDescription(description);
  req.setIsExecutable(is_executable);
  return File(req.send());
}

Execution Frontend::addExecution(const std::string& description) {
  auto req = frontend_context_.addExecutionRequest();
  req.setDescription(description);
  return Execution(req.send().then([](auto r) { return r.getExecution(); }),
                   builder_);
}

void Frontend::evaluate() {
  auto req = frontend_context_.startEvaluationRequest();
  req.setSender(kj::heap<FileProvider>(known_files_));
  builder_.AddPromise(req.send().ignoreResult());
  std::move(builder_).Finalize().wait(client_.getWaitScope());
}

void Frontend::getFileContentsAsString(
    File& file, std::function<void(const std::string&)> callback) {
  builder_.AddPromise(
      file.forked_promise.addBranch().then([this, callback](auto file) {
        auto req = frontend_context_.getFileContentsRequest();
        auto output = kj::heap<std::string>();
        auto output_ptr = output.get();
        req.setFile(file);
        req.setReceiver(kj::heap<util::File::Receiver>(
            [output = std::move(output)](util::File::Chunk data) mutable {
              *output += std::string(data.asChars().begin(), data.size());
            }));
        kj::Promise<void> ret = req.send().ignoreResult().then(
            [output_ptr, callback]() { callback(*output_ptr); });
        return std::move(ret);
      }));
}

void Frontend::getFileContentsToFile(File& file, const std::string& path,
                                     bool overwrite, bool exist_ok) {
  builder_.AddPromise(file.forked_promise.addBranch().then(
      [this, path, exist_ok, overwrite](auto file) {
        auto req = frontend_context_.getFileContentsRequest();
        req.setFile(file);
        KJ_IF_MAYBE(receiver, util::File::Write(path, overwrite, exist_ok)) {
          req.setReceiver(kj::heap<util::File::Receiver>(std::move(*receiver)));
        }
        else {
          KJ_FAIL_REQUIRE("getFileContentsToFile", strerror(errno));
        }
        return req.send().ignoreResult();
      }));
}

void Frontend::stopEvaluation() {
  frontend_context_.stopEvaluationRequest().send().wait(client_.getWaitScope());
}

void Execution::setExecutablePath(const std::string& path) {
  auto req = execution_.setExecutablePathRequest();
  req.setPath(path);
  builder_.AddPromise(req.send().ignoreResult());
}
void Execution::setExecutable(const std::string& name, File& file) {
  builder_.AddPromise(
      file.forked_promise.addBranch().then([this, name](auto file) {
        auto req = execution_.setExecutableRequest();
        req.setName(name);
        req.setFile(file);
        builder_.AddPromise(req.send().ignoreResult());
      }));
}
void Execution::setStdin(File& file) {
  builder_.AddPromise(file.forked_promise.addBranch().then([this](auto file) {
    auto req = execution_.setStdinRequest();
    req.setFile(file);
    builder_.AddPromise(req.send().ignoreResult());
  }));
}
void Execution::addInput(const std::string& name, File& file) {
  builder_.AddPromise(
      file.forked_promise.addBranch().then([this, name](auto file) {
        auto req = execution_.addInputRequest();
        req.setName(name);
        req.setFile(file);
        builder_.AddPromise(req.send().ignoreResult());
      }));
}

void Execution::setArgs(const std::vector<std::string>& args) {
  auto req = execution_.setArgsRequest();
  req.initArgs(args.size());
  for (size_t i = 0; i < args.size(); i++) {
    req.getArgs().set(i, args[i]);
  }
  builder_.AddPromise(req.send().ignoreResult());
}

void Execution::disableCache() {
  builder_.AddPromise(execution_.disableCacheRequest().send().ignoreResult());
}

void Execution::makeExclusive() {
  builder_.AddPromise(execution_.makeExclusiveRequest().send().ignoreResult());
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
  builder_.AddPromise(req.send().ignoreResult());
}

File Execution::stdout(bool is_executable) {
  auto req = execution_.stdoutRequest();
  req.setIsExecutable(is_executable);
  return File(req.send());
}

File Execution::stderr(bool is_executable) {
  auto req = execution_.stderrRequest();
  req.setIsExecutable(is_executable);
  return File(req.send());
}
File Execution::output(const std::string& name, bool is_executable) {
  auto req = execution_.outputRequest();
  req.setIsExecutable(is_executable);
  req.setName(name);
  return File(req.send());
}

void Execution::notifyStart(std::function<void()> callback) {
  builder_.AddPromise(
      execution_.notifyStartRequest().send().ignoreResult().then(callback));
}

void Execution::getResult(std::function<void(Result)> callback) {
  builder_.AddPromise(
      execution_.getResultRequest().send().then([callback](auto res) {
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
        result.resources.cpu_time = r.getResourceUsage().getCpuTime();
        result.resources.sys_time = r.getResourceUsage().getSysTime();
        result.resources.wall_time = r.getResourceUsage().getWallTime();
        result.resources.memory = r.getResourceUsage().getMemory();
        result.resources.nproc = r.getResourceUsage().getNproc();
        result.resources.nofiles = r.getResourceUsage().getNofiles();
        result.resources.fsize = r.getResourceUsage().getFsize();
        result.resources.memlock = r.getResourceUsage().getMemlock();
        result.resources.stack = r.getResourceUsage().getStack();
        callback(result);
      }));
}
}  // namespace frontend
