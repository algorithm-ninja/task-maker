#include "server/dispatcher.hpp"

#include "util/file.hpp"
#include "util/sha256.hpp"
#include "util/union_promise.hpp"

namespace server {

namespace {

kj::Promise<capnp::Response<capnproto::Evaluator::EvaluateResults>>
HandleRequest(capnproto::Evaluator::Client evaluator,
              capnproto::Request::Reader request) {
  auto req = evaluator.evaluateRequest();
  req.setRequest(request);
  return req.send().then(
      [evaluator](auto res) mutable {
        auto result = res.getResult();
        kj::Promise<void> load_files = kj::READY_NOW;
        {
          util::UnionPromiseBuilder builder;
          for (const auto& process_result : result.getProcesses()) {
            for (const auto& output : process_result.getOutputFiles()) {
              builder.AddPromise(
                  util::File::MaybeGet(output.getHash(), evaluator));
            }
            builder.AddPromise(
                util::File::MaybeGet(process_result.getStderr(), evaluator));
            builder.AddPromise(
                util::File::MaybeGet(process_result.getStdout(), evaluator));
          }
          load_files = std::move(builder).Finalize();
        }
        return load_files.then(
            [res = std::move(res)]() mutable { return std::move(res); });
      },
      [](kj::Exception exc) {
        return kj::Promise<
            capnp::Response<capnproto::Evaluator::EvaluateResults>>(
            std::move(exc));
      });
}
};  // namespace

kj::Promise<void> Dispatcher::AddEvaluator(
    capnproto::Evaluator::Client evaluator) {
  std::remove_reference_t<decltype(requests_.back())> request_info;
  do {
    if (requests_.empty()) {
      auto evaluator_promise = kj::newPromiseAndFulfiller<void>();
      evaluators_.emplace_back(evaluator);
      fulfillers_.push_back(std::move(evaluator_promise.fulfiller));
      return std::move(evaluator_promise.promise);
    }
    request_info = std::move(requests_.back());
    requests_.pop_back();
  } while (*std::get<3>(request_info));
  auto p = HandleRequest(evaluator, std::get<0>(request_info));
  // Signal execution started
  if (std::get<2>(request_info)) {
    std::get<2>(request_info)->fulfill();
  }
  auto ff = std::get<1>(request_info).get();
  return p
      .then(
          [fulfiller = ff](auto res) -> kj::Promise<void> {
            fulfiller->fulfill(std::move(res));
            return kj::READY_NOW;
          },
          [this, request = std::get<0>(request_info),
           fulfiller = std::move(std::get<1>(request_info)),
           canceled = std::get<3>(request_info)](
              kj::Exception exc) mutable -> kj::Promise<void> {
            KJ_LOG(WARNING, "Worker failed");
            kj::PromiseFulfillerPair<void> dummy_start =
                kj::newPromiseAndFulfiller<void>();
            dummy_start.promise.then([]() { KJ_LOG(INFO, "Retrying..."); })
                .detach([](kj::Exception exc) {
                  KJ_FAIL_ASSERT("dummy_start rejected", exc.getDescription());
                });
            auto ff = fulfiller.get();
            return AddRequest(request, std::move(dummy_start.fulfiller),
                              canceled)
                .then(
                    [fulfiller = std::move(fulfiller)](auto res) mutable {
                      fulfiller->fulfill(std::move(res));
                    },
                    [fulfiller = ff](kj::Exception exc) {
                      fulfiller->reject(kj::cp(exc));
                      return exc;
                    });
          })
      .eagerlyEvaluate(nullptr);
}

kj::Promise<capnp::Response<capnproto::Evaluator::EvaluateResults>>
Dispatcher::AddRequest(capnproto::Request::Reader request,
                       kj::Own<kj::PromiseFulfiller<void>> fulfiller,
                       std::shared_ptr<bool>& canceled) {
  if (evaluators_.empty()) {
    auto request_promise = kj::newPromiseAndFulfiller<
        capnp::Response<capnproto::Evaluator::EvaluateResults>>();
    requests_.emplace_back(request, std::move(request_promise.fulfiller),
                           std::move(fulfiller), canceled);
    return std::move(request_promise.promise);
  }
  auto evaluator = std::move(evaluators_.back());
  evaluators_.pop_back();
  auto evaluator_fulfiller = std::move(fulfillers_.back());
  fulfillers_.pop_back();
  fulfiller->fulfill();
  auto p = HandleRequest(evaluator, request);
  auto ff = evaluator_fulfiller.get();
  return p
      .then(
          [fulfiller = ff](auto result) mutable
          -> kj::Promise<
              capnp::Response<capnproto::Evaluator::EvaluateResults>> {
            fulfiller->fulfill();
            return std::move(result);
          },
          [this, request, canceled, fulfiller = std::move(evaluator_fulfiller)](
              kj::Exception exc) mutable
          -> kj::Promise<
              capnp::Response<capnproto::Evaluator::EvaluateResults>> {
            KJ_LOG(WARNING, "Worker failed");
            kj::PromiseFulfillerPair<void> dummy_start =
                kj::newPromiseAndFulfiller<void>();
            dummy_start.promise.then([]() { KJ_LOG(INFO, "Retrying..."); })
                .detach([](kj::Exception exc) {
                  KJ_FAIL_ASSERT("dummy_start rejected", exc.getDescription());
                });
            fulfiller->reject(KJ_EXCEPTION(FAILED, kj::cp(exc)));
            return AddRequest(request, std::move(dummy_start.fulfiller),
                              canceled);
          })
      .eagerlyEvaluate(nullptr);
}

}  // namespace server
