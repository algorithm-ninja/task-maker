#include "server/dispatcher.hpp"

#include "util/file.hpp"
#include "util/sha256.hpp"
#include "util/union_promise.hpp"

namespace server {

kj::Promise<capnp::Response<capnproto::Evaluator::EvaluateResults>>
Dispatcher::HandleRequest(capnproto::Evaluator::Client evaluator,
                          capnproto::Request::Reader request) {
  auto req = evaluator.evaluateRequest();
  req.setRequest(request);
  size_t client = client_cnt_++;
  running_[client] = std::make_unique<capnproto::Evaluator::Client>(evaluator);
  return req.send().then(
      [evaluator, client, this](auto res) mutable {
        running_.erase(client);
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
      [client, this](kj::Exception exc) {
        running_.erase(client);
        return kj::Promise<
            capnp::Response<capnproto::Evaluator::EvaluateResults>>(
            std::move(exc));
      });
}

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
    request_info = std::move(requests_.front());
    requests_.pop();
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
           canceled = std::get<3>(request_info),
           retries = std::get<4>(request_info)](
              kj::Exception exc) mutable -> kj::Promise<void> {
            KJ_LOG(WARNING, "Worker failed");
            if (*canceled) {
              fulfiller->reject(kj::cp(exc));
              KJ_LOG(INFO, "Request canceled");
              return exc;
            }
            if (retries == 0) {
              fulfiller->reject(kj::cp(exc));
              KJ_LOG(WARNING, "Retries exhausted");
              return exc;
            }
            kj::PromiseFulfillerPair<void> dummy_start =
                kj::newPromiseAndFulfiller<void>();
            dummy_start.promise.then([]() { KJ_LOG(INFO, "Retrying..."); })
                .detach([](kj::Exception exc) {
                  KJ_LOG(WARNING, "dummy_start rejected", exc.getDescription());
                });
            auto ff = fulfiller.get();
            return AddRequest(request, std::move(dummy_start.fulfiller),
                              canceled, retries - 1)
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
                       kj::Own<kj::PromiseFulfiller<void>> notify,
                       const std::shared_ptr<bool>& canceled, size_t retries) {
  if (*canceled || canceled_evaluations_.count(request.getEvaluationId())) {
    return KJ_EXCEPTION(FAILED, "Enqueueing canceled request");
  }
  if (evaluators_.empty()) {
    auto request_promise = kj::newPromiseAndFulfiller<
        capnp::Response<capnproto::Evaluator::EvaluateResults>>();
    requests_.emplace(request, std::move(request_promise.fulfiller),
                      std::move(notify), canceled, retries);
    return std::move(request_promise.promise);
  }
  auto evaluator = std::move(evaluators_.back());
  evaluators_.pop_back();
  auto evaluator_fulfiller = std::move(fulfillers_.back());
  fulfillers_.pop_back();
  notify->fulfill();
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
          [this, request, canceled, retries,
           fulfiller =
               std::move(evaluator_fulfiller)](kj::Exception exc) mutable
          -> kj::Promise<
              capnp::Response<capnproto::Evaluator::EvaluateResults>> {
            KJ_LOG(WARNING, "Worker failed");
            fulfiller->reject(KJ_EXCEPTION(FAILED, kj::cp(exc)));
            if (retries == 0) {
              KJ_LOG(WARNING, "Retries exhausted");
              return exc;
            }
            if (*canceled ||
                canceled_evaluations_.count(request.getEvaluationId())) {
              return KJ_EXCEPTION(FAILED, "Enqueueing canceled request");
            }
            kj::PromiseFulfillerPair<void> dummy_start =
                kj::newPromiseAndFulfiller<void>();
            dummy_start.promise.then([]() { KJ_LOG(INFO, "Retrying..."); })
                .detach([](kj::Exception exc) {
                  KJ_LOG(WARNING, "dummy_start rejected", exc.getDescription());
                });
            return AddRequest(request, std::move(dummy_start.fulfiller),
                              canceled, retries - 1);
          })
      .eagerlyEvaluate(nullptr);
}

kj::Promise<void> Dispatcher::Cancel(uint32_t frontend_id) {
  canceled_evaluations_.insert(frontend_id);
  util::UnionPromiseBuilder builder;
  for (auto& kv : running_) {
    auto req = kv.second->cancelRequestRequest();
    req.setEvaluationId(frontend_id);
    builder.AddPromise(req.send().ignoreResult());
  }
  return std::move(builder).Finalize();
}

}  // namespace server
