#ifndef WORKER_EXECUTOR_HPP
#define WORKER_EXECUTOR_HPP

#include <mutex>

#include "capnp/evaluation.capnp.h"
#include "sandbox/sandbox.hpp"
#include "util/file.hpp"

namespace worker {

class Executor : public capnproto::Evaluator::Server {
 public:
  KJ_DISALLOW_COPY(Executor);
  Executor(capnproto::FileSender::Client server) : server_(server) {}

  kj::Promise<void> Evaluate(EvaluateContext context) {
    auto request = context.getParams().getRequest();
    return Execute(request, context.getResults().initResult());
  }

  kj::Promise<void> RequestFile(RequestFileContext context) {
    return util::File::HandleRequestFile(context);
  }

 private:
  kj::Promise<void> Execute(capnproto::Request::Reader request,
                            capnproto::Result::Builder result);

  static const constexpr char* kBoxDir = "box";

  // Get a file from the server, if needed.
  kj::Promise<void> MaybeGetFile(const util::SHA256_t& hash)
      KJ_WARN_UNUSED_RESULT {
    if (hash.isZero()) return kj::READY_NOW;
    if (!util::File::Exists(util::File::PathForHash(hash))) {
      return GetFile(hash);
    } else {
      return kj::READY_NOW;
    }
  }
  kj::Promise<void> GetFile(const util::SHA256_t& hash) {
    auto req = server_.requestFileRequest();
    hash.ToCapnp(req.initHash());
    req.setReceiver(kj::heap<util::File::Receiver>(hash));
    return req.send().ignoreResult();
  }
  capnproto::FileSender::Client server_;
};

}  // namespace worker

#endif
