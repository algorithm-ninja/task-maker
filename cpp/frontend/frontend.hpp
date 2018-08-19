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
  template <typename T>
  explicit File(T&& prom)
      : promise(prom.then([](auto r) { return r.getFile(); })),
        forked_promise(promise.fork()) {}
};

class Execution {
 public:
  Execution(capnproto::Execution::Client execution,
            util::UnionPromiseBuilder& builder)
      : execution_(execution), builder_(builder) {}

  void setExecutablePath(const std::string& path);
  void setExecutable(const std::string& name, File& file);
  void setStdin(File& file);
  void addInput(const std::string& name, File& file);

  void setArgs(const std::vector<std::string>& args);

  void disableCache();
  void makeExclusive();
  void setLimits(const Resources& limits);

  File stdout(bool is_executable);
  File stderr(bool is_executable);
  File output(const std::string& name, bool is_executable);

  void notifyStart(std::function<void()> callback);

  void getResult(std::function<void(Result)> callback);

 private:
  capnproto::Execution::Client execution_;
  util::UnionPromiseBuilder& builder_;
};

class Frontend {
 public:
  Frontend(std::string server, int port);

  File provideFile(const std::string& path, const std::string& description,
                   bool is_executable);
  Execution addExecution(const std::string& description);
  void evaluate();  // Starts evaluation and returns when complete.
  void getFileContentsAsString(
      File& file, std::function<void(const std::string&)> callback);
  void getFileContentsToFile(File& file, const std::string& path,
                             bool overwrite, bool exist_ok);
  void stopEvaluation();

 private:
  capnp::EzRpcClient client_;
  capnproto::FrontendContext::Client frontend_context_;
  std::unordered_map<util::SHA256_t, std::string, util::SHA256_t::Hasher>
      known_files_;
  util::UnionPromiseBuilder builder_;
};
}  // namespace frontend

#endif
