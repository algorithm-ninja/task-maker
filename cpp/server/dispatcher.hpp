#ifndef SERVER_DISPATCHER_HPP
#define SERVER_DISPATCHER_HPP

#include <kj/async.h>
#include <vector>
#include "capnp/evaluation.capnp.h"

namespace server {

class Dispatcher {
  template <typename T, typename U>
  using Queue = std::vector<std::tuple<T, kj::Own<kj::PromiseFulfiller<U>>,
                                       kj::Own<kj::PromiseFulfiller<void>>>>;

 public:
  kj::Promise<void> AddEvaluator(capnproto::Evaluator::Client evaluator)
      KJ_WARN_UNUSED_RESULT;
  kj::Promise<capnp::Response<capnproto::Evaluator::EvaluateResults>>
  AddRequest(capnproto::Request::Reader request,
             kj::Own<kj::PromiseFulfiller<void>> notify) KJ_WARN_UNUSED_RESULT;

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
