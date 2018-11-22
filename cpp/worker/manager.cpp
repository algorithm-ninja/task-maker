#include "worker/manager.hpp"
#include "util/flags.hpp"
#include "worker/executor.hpp"

#include <fcntl.h>
#include <csignal>
#include <sys/wait.h>
#include <unistd.h>

#include <thread>
#include <unordered_set>

#include <capnp/ez-rpc.h>
#include "capnp/server.capnp.h"
#include "worker/executor.hpp"

#define check_error(op)                                           \
  if ((op) == -1) {                                               \
    throw std::runtime_error(std::string(#op) + strerror(errno)); \
  }

namespace worker {
void Manager::Run() {
  OnDone();
  on_error_.promise.wait(client_.getWaitScope());
}

void Manager::OnDone() {
  if (running_cores_ + reserved_cores_ < num_cores_) {
    while (pending_requests_ < max_pending_requests_) {
      pending_requests_++;
      auto server = client_.getMain<capnproto::MainServer>();
      auto req = server.registerEvaluatorRequest();
      req.setName(name_ + " " + std::to_string(last_worker_id_++));
      req.setEvaluator(kj::heap<Executor>(server, this, &cache_));
      req.send().detach([this](kj::Exception exc) {
        on_error_.fulfiller->reject(std::move(exc));
      });
    }
  }
  while (!waiting_tasks_.empty()) {
    int sz = waiting_tasks_.front().first;
    if (running_cores_ + sz > num_cores_) break;
    reserved_cores_ -= sz;
    running_cores_ += sz;
    waiting_tasks_.front().second->fulfill();
    waiting_tasks_.pop();
  }
}

void Manager::CancelPending() {
  pending_requests_--;
  OnDone();
}

}  // namespace worker
