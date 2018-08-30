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
#include "util/sha256.hpp"
#include "util/union_promise.hpp"

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
  capnproto::ProcessResult::Status::Which status;
  uint32_t signal;
  uint32_t return_code;
  std::string error;
  Resources resources;
  bool was_killed;
  bool was_cached;
};

class Frontend;

class Fifo {
  friend class Execution;
  friend class ExecutionGroup;
  kj::Promise<capnproto::Fifo::Reader> promise;
  kj::ForkedPromise<capnproto::Fifo::Reader> forked_promise;

 protected:
  void SetPromise(kj::Promise<capnproto::Fifo::Reader>&& prom) {
    promise = std::move(prom);
    forked_promise = promise.fork();
  }

 public:
  Fifo() : promise(capnproto::Fifo::Reader()), forked_promise(promise.fork()) {}
  virtual ~Fifo() = default;
  template <typename T>
  static std::unique_ptr<Fifo> New(kj::Promise<T>&& p);
};

template <typename T>
class FifoInst : public Fifo {
 public:
  FifoInst(T&& p)
      : pf(kj::newPromiseAndFulfiller<capnproto::Fifo::Reader>()),
        promise(std::move(p)) {
    SetPromise(std::move(pf.promise));
    promise = promise
                  .then(
                      [this](auto res) {
                        pf.fulfiller->fulfill(res.getFifo());
                        return std::move(res);
                      },
                      [this](kj::Exception exc) {
                        pf.fulfiller->rejectIfThrows(
                            []() { KJ_FAIL_ASSERT("Request failed"); });
                        return exc;
                      })
                  .eagerlyEvaluate(nullptr);
  }

 private:
  kj::PromiseFulfillerPair<capnproto::Fifo::Reader> pf;
  T promise;
};

template <typename T>
std::unique_ptr<Fifo> Fifo::New(kj::Promise<T>&& p) {
  return std::make_unique<FifoInst<kj::Promise<T>>>(std::move(p));
}

class File {
  friend class Frontend;
  friend class Execution;
  kj::Promise<capnproto::File::Reader> promise;
  kj::ForkedPromise<capnproto::File::Reader> forked_promise;
  bool is_executable_;

 protected:
  Frontend& frontend_;

  void SetPromise(kj::Promise<capnproto::File::Reader>&& prom) {
    promise = std::move(prom);
    forked_promise = promise.fork();
  }
  File(Frontend& frontend, bool is_executable)
      : promise(capnproto::File::Reader()),
        forked_promise(promise.fork()),
        is_executable_(is_executable),
        frontend_(frontend) {}

 public:
  template <typename T>
  static std::unique_ptr<File> New(kj::Promise<T>&& p, Frontend& frontend,
                                   bool is_executable);
  virtual ~File() = default;

  void getContentsAsString(std::function<void(const std::string&)> callback);
  void getContentsToFile(const std::string& path, bool overwrite,
                         bool exist_ok);
};

template <typename T>
class FileInst : public File {
 public:
  FileInst(T&& p, Frontend& frontend, bool is_executable)
      : File(frontend, is_executable),
        pf(kj::newPromiseAndFulfiller<capnproto::File::Reader>()),
        promise(std::move(p)) {
    SetPromise(std::move(pf.promise));
    promise = promise
                  .then(
                      [this](auto res) {
                        pf.fulfiller->fulfill(res.getFile());
                        return std::move(res);
                      },
                      [this](kj::Exception exc) {
                        pf.fulfiller->rejectIfThrows(
                            []() { KJ_FAIL_ASSERT("Request failed"); });
                        return exc;
                      })
                  .eagerlyEvaluate(nullptr);
  }

 private:
  kj::PromiseFulfillerPair<capnproto::File::Reader> pf;
  T promise;
};

template <typename T>
std::unique_ptr<File> File::New(kj::Promise<T>&& p, Frontend& frontend,
                                bool is_executable) {
  return std::make_unique<FileInst<kj::Promise<T>>>(std::move(p), frontend,
                                                    is_executable);
}

class Execution {
 public:
  Execution(std::string description, capnproto::Execution::Client execution,
            std::vector<std::unique_ptr<File>>& files,
            util::UnionPromiseBuilder& builder,
            util::UnionPromiseBuilder& finish_builder, Frontend& frontend)
      : description_(std::move(description)),
        execution_(execution),
        files_(files),
        builder_(builder),
        finish_builder_(finish_builder),
        frontend_(frontend) {}

  void setExecutablePath(const std::string& path);
  void setExecutable(const std::string& name, File* file);
  void setStdin(File* file);
  void addInput(const std::string& name, File* file);
  void addFifo(const std::string& name, Fifo* fifo);
  void setStdinFifo(Fifo* fifo);
  void setStdoutFifo(Fifo* fifo);
  void setStderrFifo(Fifo* fifo);

  void setArgs(const std::vector<std::string>& args);

  void disableCache();
  void makeExclusive();
  void setLimits(const Resources& limits);
  void setExtraTime(float extra_time);

  File* stdout(bool is_executable);
  File* stderr(bool is_executable);
  File* output(const std::string& name, bool is_executable);

  void notifyStart(std::function<void()> callback);

  void getResult(std::function<void(Result)> callback,
                 std::function<void()> errored = nullptr);

 private:
  std::string description_;
  capnproto::Execution::Client execution_;
  std::vector<std::unique_ptr<File>>& files_;
  util::UnionPromiseBuilder& builder_;
  util::UnionPromiseBuilder& finish_builder_;
  util::UnionPromiseBuilder my_builder_;
  Frontend& frontend_;
};

class ExecutionGroup {
 public:
  ExecutionGroup(std::string description,
                 capnproto::ExecutionGroup::Client execution_group,
                 std::vector<std::unique_ptr<File>>& files,
                 util::UnionPromiseBuilder& builder,
                 util::UnionPromiseBuilder& finish_builder, Frontend& frontend)
      : description_(std::move(description)),
        execution_group_(execution_group),
        files_(files),
        builder_(builder),
        finish_builder_(finish_builder),
        frontend_(frontend) {}
  Execution* addExecution(const std::string& description);
  Fifo* createFifo();

 private:
  std::vector<std::unique_ptr<Execution>> executions_;
  std::vector<std::unique_ptr<Fifo>> fifos_;
  std::string description_;
  capnproto::ExecutionGroup::Client execution_group_;
  std::vector<std::unique_ptr<File>>& files_;
  util::UnionPromiseBuilder& builder_;
  util::UnionPromiseBuilder& finish_builder_;
  util::UnionPromiseBuilder my_builder_;
  Frontend& frontend_;
};

class Frontend {
  friend class File;

 public:
  Frontend(std::string server, int port);

  File* provideFile(const std::string& path, const std::string& description,
                    bool is_executable);
  Execution* addExecution(const std::string& description);
  ExecutionGroup* addExecutionGroup(const std::string& description);
  void evaluate();  // Starts evaluation and returns when complete.
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
  std::vector<std::unique_ptr<ExecutionGroup>> groups_;
  kj::Promise<void> stop_request_;
};
}  // namespace frontend

#endif
