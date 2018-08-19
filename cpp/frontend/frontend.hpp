#ifndef FRONTEND_FRONTEND_HPP
#define FRONTEND_FRONTEND_HPP
#include <capnp/ez-rpc.h>
#include <kj/async.h>
#include <functional>
#include <string>
#include <unordered_map>
#include <vector>

#include "capnp/server.capnp.h"
#include "util/file.hpp"
#include "util/misc.hpp"
#include "util/sha256.hpp"

namespace frontend {

struct Resources {
  float cpu_time;
  float sys_time;
  float wall_time;
  uint64_t memory;
  uint32_t nproc;
  uint32_t nofiles;
  uint64_t fsize;
  uint64_t memlock;
  uint64_t stack;
};

struct Result {
  capnproto::Result::Status::Which status;
  uint32_t signal;
  uint32_t return_code;
  std::string error;
  Resources resources;
};

class File {
  friend class Frontend;
  friend class Execution;
  kj::Promise<capnproto::File::Reader> promise;
  kj::ForkedPromise<capnproto::File::Reader> forked_promise;

 protected:
  void SetPromise(kj::Promise<capnproto::File::Reader>&& prom) {
    promise = std::move(prom);
    forked_promise = promise.fork();
  }
  File() : promise(capnproto::File::Reader()), forked_promise(promise.fork()) {}

 public:
  template <typename T>
  static std::unique_ptr<File> New(kj::Promise<T>&& p);
  virtual ~File() = default;
};

template <typename T>
class FileInst : public File {
 public:
  FileInst(T&& p)
      : pf(kj::newPromiseAndFulfiller<capnproto::File::Reader>()),
        promise(std::move(p)) {
    SetPromise(std::move(pf.promise));
    promise = promise
                  .then([this](auto res) {
                    pf.fulfiller->fulfill(res.getFile());
                    return std::move(res);
                  })
                  .eagerlyEvaluate(nullptr);
  }

 private:
  kj::PromiseFulfillerPair<capnproto::File::Reader> pf;
  T promise;
};

template <typename T>
std::unique_ptr<File> File::New(kj::Promise<T>&& p) {
  return std::make_unique<FileInst<kj::Promise<T>>>(std::move(p));
}

class Execution {
 public:
  Execution(capnproto::Execution::Client execution,
            std::vector<std::unique_ptr<File>>& files,
            util::UnionPromiseBuilder& builder,
            util::UnionPromiseBuilder& finish_builder)
      : execution_(execution),
        files_(files),
        builder_(builder),
        finish_builder_(finish_builder) {}

  void setExecutablePath(const std::string& path);
  void setExecutable(const std::string& name, File* file);
  void setStdin(File* file);
  void addInput(const std::string& name, File* file);

  void setArgs(const std::vector<std::string>& args);

  void disableCache();
  void makeExclusive();
  void setLimits(const Resources& limits);

  File* stdout(bool is_executable);
  File* stderr(bool is_executable);
  File* output(const std::string& name, bool is_executable);

  void notifyStart(std::function<void()> callback);

  void getResult(std::function<void(Result)> callback);

 private:
  capnproto::Execution::Client execution_;
  std::vector<std::unique_ptr<File>>& files_;
  util::UnionPromiseBuilder& builder_;
  util::UnionPromiseBuilder& finish_builder_;
  util::UnionPromiseBuilder my_builder_;
};

class Frontend {
 public:
  Frontend(std::string server, int port);

  File* provideFile(const std::string& path, const std::string& description,
                    bool is_executable);
  Execution* addExecution(const std::string& description);
  void evaluate();  // Starts evaluation and returns when complete.
  void getFileContentsAsString(
      File* file, std::function<void(const std::string&)> callback);
  void getFileContentsToFile(File* file, const std::string& path,
                             bool overwrite, bool exist_ok);
  void stopEvaluation();

 private:
  capnp::EzRpcClient client_;
  capnproto::FrontendContext::Client frontend_context_;
  std::unordered_map<util::SHA256_t, std::string, util::SHA256_t::Hasher>
      known_files_;
  util::UnionPromiseBuilder builder_;
  util::UnionPromiseBuilder finish_builder_;
  std::vector<std::unique_ptr<File>> files_;
  std::vector<std::unique_ptr<Execution>> executions_;
  kj::Promise<void> stop_request_;
};
}  // namespace frontend

#endif
