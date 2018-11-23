#ifndef SERVER_DISPATCHER_HPP
#define SERVER_DISPATCHER_HPP

#include <kj/async.h>
#include <memory>
#include <vector>
#include "capnp/evaluation.capnp.h"

namespace server {

// Class to dispatch execution requests to workers.
class Dispatcher {
  template <typename T, typename U>
  using Queue = std::vector<
      std::tuple<T, kj::Own<kj::PromiseFulfiller<U>>,
                 kj::Own<kj::PromiseFulfiller<void>>, std::shared_ptr<bool>>>;

 public:
  // Adds a new evaluator to the worker queue. Returns a promise that will
  // resolve when the worker has executed a request.
  kj::Promise<void> AddEvaluator(capnproto::Evaluator::Client evaluator)
      KJ_WARN_UNUSED_RESULT;

  // Adds a new request to the request queue. Returns a promise that will
  // resolve when some worker has finished running the request. When a worker
  // is available:
  //  - if the request has been cancelled by setting cancelled to true,
  //    the promise will be rejected.
  //  - otherwise, notify->fulfill() will be called, the request will be
  //    dispatched to the worker and the promise will resolve when the worker
  //    completes the execution.
  kj::Promise<capnp::Response<capnproto::Evaluator::EvaluateResults>>
  AddRequest(capnproto::Request::Reader request,
             kj::Own<kj::PromiseFulfiller<void>> notify,
             const std::shared_ptr<bool>& canceled) KJ_WARN_UNUSED_RESULT;

 private:
  // TODO: I could not make a Queue<Evaluator, void> work, for some reason
  std::vector<capnproto::Evaluator::Client> evaluators_;
  std::vector<kj::Own<kj::PromiseFulfiller<void>>> fulfillers_;
  Queue<capnproto::Request::Reader,
        capnp::Response<capnproto::Evaluator::EvaluateResults>>
      requests_;
};

}  // namespace server

#endif
