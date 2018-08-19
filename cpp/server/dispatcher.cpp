#include "server/dispatcher.hpp"

#include "util/file.hpp"
#include "util/misc.hpp"
#include "util/sha256.hpp"

namespace server {

namespace {

kj::Promise<capnp::Response<capnproto::Evaluator::EvaluateResults>>
HandleRequest(capnproto::Evaluator::Client evaluator,
              capnproto::Request::Reader request) {
  auto req = evaluator.evaluateRequest();
  req.setRequest(request);
  return req.send().then([evaluator](auto res) mutable {
    auto result = res.getResult();
    kj::Promise<void> load_files = kj::READY_NOW;
    {
      util::UnionPromiseBuilder builder;
      for (const auto& output : result.getOutputFiles()) {
        builder.AddPromise(util::File::MaybeGet(output.getHash(), evaluator));
      }
      builder.AddPromise(util::File::MaybeGet(result.getStderr(), evaluator));
      builder.AddPromise(util::File::MaybeGet(result.getStdout(), evaluator));
      load_files = std::move(builder).Finalize();
    }
    return load_files.then(
        [res = std::move(res)]() mutable { return std::move(res); });
  });
}
};  // namespace

kj::Promise<void> Dispatcher::AddEvaluator(
    capnproto::Evaluator::Client evaluator) {
  if (requests_.empty()) {
    auto evaluator_promise = kj::newPromiseAndFulfiller<void>();
    evaluators_.emplace_back(evaluator);
    fulfillers_.push_back(std::move(evaluator_promise.fulfiller));
    return std::move(evaluator_promise.promise);
  }
  auto request_info = std::move(requests_.back());
  requests_.pop_back();
  auto p = HandleRequest(evaluator, std::get<0>(request_info));
  // Signal execution started
  if (std::get<2>(request_info)) {
    std::get<2>(request_info)->fulfill();
  }
  return p
      .then(
          [request_fulfiller = std::move(std::get<1>(request_info))](
              auto res) mutable { request_fulfiller->fulfill(std::move(res)); },
          [](kj::Exception exc) { KJ_FAIL_ASSERT(exc); })
      .eagerlyEvaluate(nullptr);
}

kj::Promise<capnp::Response<capnproto::Evaluator::EvaluateResults>>
Dispatcher::AddRequest(capnproto::Request::Reader request,
                       kj::Own<kj::PromiseFulfiller<void>> fulfiller) {
  if (evaluators_.empty()) {
    auto request_promise = kj::newPromiseAndFulfiller<
        capnp::Response<capnproto::Evaluator::EvaluateResults>>();
    requests_.emplace_back(request, std::move(request_promise.fulfiller),
                           std::move(fulfiller));
    return std::move(request_promise.promise);
  }
  auto evaluator = std::move(evaluators_.back());
  evaluators_.pop_back();
  auto evaluator_fulfiller = std::move(fulfillers_.back());
  fulfillers_.pop_back();
  fulfiller->fulfill();
  auto p = HandleRequest(evaluator, request);
  return p
      .then([evaluator_fulfiller =
                 std::move(evaluator_fulfiller)](auto result) mutable {
        evaluator_fulfiller->fulfill();
        return std::move(result);
      })
      .eagerlyEvaluate(nullptr);
}

}  // namespace server
