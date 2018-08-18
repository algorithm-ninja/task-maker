#include "worker/manager.hpp"
#include "util/flags.hpp"
#include "worker/executor.hpp"

#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>

#include <thread>
#include <unordered_set>

#include <capnp/ez-rpc.h>
#include "capnp/server.capnp.h"

#define check_error(op)                                           \
  if ((op) == -1) {                                               \
    throw std::runtime_error(std::string(#op) + strerror(errno)); \
  }

namespace worker {
namespace {
int pipefd[2];

void Worker() {
  capnp::EzRpcClient client(Flags::server, Flags::port);
  capnproto::MainServer::Client server =
      client.getMain<capnproto::MainServer>();
  auto req = server.registerEvaluatorRequest();
  req.setName(Flags::name + " (pid: " + std::to_string(getpid()) + ")");
  req.setEvaluator(kj::heap<Executor>(server));
  auto finish = req.send();
  // We wait until the server terminates the registerEvaluator call,
  // which should happen when it has finished interacting with us,
  // then we kill the worker.
  finish.wait(client.getWaitScope());
}

void ManagerFun() {
  signal(SIGTERM, SIG_IGN);
  signal(SIGINT, SIG_IGN);
  signal(SIGQUIT, SIG_IGN);
  signal(SIGHUP, SIG_IGN);
  int parentfd = pipefd[0];
  int flags = fcntl(parentfd, F_GETFL, 0);
  fcntl(parentfd, F_SETFL, flags | O_NONBLOCK);
  if (Flags::num_cores == 0) {
    Flags::num_cores = std::thread::hardware_concurrency();
  }
  size_t num_boxes = Flags::num_cores;
  ssize_t num_read = 0;
  std::unordered_set<int> children;
  while ((num_read = read(parentfd, &num_boxes, sizeof(size_t))) != 0) {
    if (errno != EAGAIN && errno != EWOULDBLOCK) {
      check_error(num_read);
    }
    if (children.size() < num_boxes) {
      pid_t pid;
      check_error(pid = fork());
      if (pid == 0) {
        Worker();
        _Exit(0);
      }
      children.insert(pid);
      continue;
    }
    pid_t pid;
    int wstatus;
    if ((pid = waitpid(-1, &wstatus, WNOHANG)) > 0) {
      children.erase(pid);
      continue;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  // FD closed, parent has terminated.
  // TODO: wait for the sandboxes to exit gracefully?
  for (int c : children) {
    kill(SIGTERM, c);
  }
  for (int c : children) {
    int wstatus;
    waitpid(c, &wstatus, 0);
  }
}
}  // namespace

void Manager::Start() {
  // Create pipe for communication with the sandbox manager
  check_error(pipe(pipefd));

  // Start the Manager process
  pid_t pid;
  check_error(pid = fork());
  if (pid == 0) {
    close(pipefd[1]);
    ManagerFun();
    _Exit(0);
  } else {
    close(pipefd[0]);
    // Ignore SIGCHLD so that the manager can die later than us
    signal(SIGCHLD, SIG_IGN);
  }
}

void Manager::Stop() { close(pipefd[1]); }

void Manager::ChangeNumWorker(size_t num) {
  check_error(write(pipefd[1], &num, sizeof(num)));
}
}  // namespace worker
