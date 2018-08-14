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

  capnproto::FileSender::Client server_;
};

}  // namespace worker

#endif
