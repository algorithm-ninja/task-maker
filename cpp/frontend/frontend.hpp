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

// Resource usage/limit for an execution. Fields have the same meaning as the
// corresponding capnproto message.
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

// Result of an execution.
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

// Represents a Fifo to be passed to an Execution.
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
  Fifo(const Fifo&) = delete;
  Fifo(Fifo&&) = default;
  Fifo& operator=(const Fifo&) = delete;
  Fifo& operator=(Fifo&&) = default;
  template <typename T>
  static std::unique_ptr<Fifo> New(kj::Promise<T>&& p);
};

// Represents a file to be passed to an Execution.
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
  File(Frontend* frontend, bool is_executable)
      : promise(capnproto::File::Reader()),
        forked_promise(promise.fork()),
        is_executable_(is_executable),
        frontend_(*frontend) {}

 public:
  template <typename T>
  static std::unique_ptr<File> New(kj::Promise<T>&& p, Frontend* frontend,
                                   bool is_executable);
  virtual ~File() = default;
  File(const File&) = delete;
  File(File&&) = delete;
  File& operator=(const File&) = delete;
  File& operator=(File&&) = delete;

  // Call the provided callback with the contents of the file as soon as they
  // are available.
  void getContentsAsString(
      const std::function<void(const std::string&)>& callback,
      uint64_t limit = 0xffffffffffffffff);

  // Write the file to path when it is available.
  void getContentsToFile(const std::string& path, bool overwrite,
                         bool exist_ok);
};

// Class representing a specific execution. Methods are proxies to the ones in
// the respective capnproto interface. No method of this class should be called
// after calling getResult. getResult should be called at least once, otherwise
// the execution will not run.
class Execution {
 public:
  Execution(std::string description, capnproto::Execution::Client execution,
            std::vector<std::unique_ptr<File>>* files,
            util::UnionPromiseBuilder* builder,
            util::UnionPromiseBuilder* finish_builder, Frontend* frontend)
      : description_(std::move(description)),
        execution_(std::move(execution)),
        files_(*files),
        builder_(*builder),
        finish_builder_(*finish_builder),
        frontend_(*frontend) {}

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

  File* getStdout(bool is_executable);
  File* getStderr(bool is_executable);
  File* getOutput(const std::string& name, bool is_executable);

  void notifyStart(const std::function<void()>& callback);

  void getResult(const std::function<void(Result)>& callback,
                 const std::function<void()>& errored = nullptr);

 private:
  std::string description_;
  capnproto::Execution::Client execution_;
  std::vector<std::unique_ptr<File>>& files_;
  util::UnionPromiseBuilder& builder_;
  util::UnionPromiseBuilder& finish_builder_;
  util::UnionPromiseBuilder my_builder_;
  Frontend& frontend_;
};

// Class representing a group of executions. Methods are proxies to the ones in
// the respective capnproto interface.
class ExecutionGroup {
 public:
  ExecutionGroup(std::string description,
                 capnproto::ExecutionGroup::Client execution_group,
                 std::vector<std::unique_ptr<File>>* files,
                 util::UnionPromiseBuilder* builder,
                 util::UnionPromiseBuilder* finish_builder, Frontend* frontend)
      : description_(std::move(description)),
        execution_group_(std::move(execution_group)),
        files_(*files),
        builder_(*builder),
        finish_builder_(*finish_builder),
        frontend_(*frontend) {}
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

// Frontend that communicates with a specific server on a given port.
class Frontend {
  friend class File;

 public:
  Frontend(const std::string& server, int port);

  // Defines a file that is provided by the frontend, loading it from the given
  // path.
  File* provideFile(const std::string& path, const std::string& description,
                    bool is_executable);

  // Defines a file that is provided by the frontend, loading it from its
  // content.
  File* provideFileContent(const std::string& content,
                           const std::string& description, bool is_executable);

  // Creates a new execution with the given description.
  Execution* addExecution(const std::string& description);

  // Creates a new execution group with the given description.
  ExecutionGroup* addExecutionGroup(const std::string& description);

  // Starts evaluation and returns when complete. Should only be called after
  // all the executions are defined.
  void evaluate();

  // Stops the evaluation. This is best-effort: some executions may still run
  // after this method is called.
  void stopEvaluation();

 private:
  capnp::EzRpcClient client_;
  capnproto::FrontendContext::Client frontend_context_;
  std::unordered_map<util::SHA256_t, util::FileWrapper, util::SHA256_t::Hasher>
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
