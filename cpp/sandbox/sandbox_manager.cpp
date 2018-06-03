#include "sandbox/sandbox_manager.hpp"
#include "sandbox/sandbox.hpp"
#include "util/ipc.hpp"

#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>
#include <atomic>
#include <condition_variable>
#include <mutex>
#include <thread>

#define check_error(op)                                           \
  if ((op) == -1) {                                               \
    throw std::runtime_error(std::string(#op) + strerror(errno)); \
  }

struct ExecutionRequest {
  size_t id;
  sandbox::ExecutionOptions options;
};

struct ExecutionAnswer {
  size_t id;
  bool status;
  char error_msg[8192];
  sandbox::ExecutionInfo info;
};

namespace sandbox {
namespace {
const constexpr size_t queue_size = 16;
int pipefd[2];
std::thread response_receiver;
std::unique_ptr<SharedQueue<ExecutionRequest>> requests;
std::unique_ptr<SharedQueue<ExecutionAnswer>> answers;
std::atomic<size_t> next_id;

std::unordered_map<size_t, ExecutionAnswer> received_answers;
std::mutex received_answers_mutex;
std::condition_variable received_answers_cv;

void ResponseReceiver() {
  ExecutionAnswer answer;
  while (answers->Dequeue(&answer)) {
    std::unique_lock<std::mutex> lck(received_answers_mutex);
    received_answers[answer.id] = answer;
    received_answers_cv.notify_all();
  }
}
void Sandbox() {
  ExecutionRequest req{0, {"", ""}};
  std::unique_ptr<sandbox::Sandbox> sb = Sandbox::Create();
  if (!requests->Dequeue(&req)) {
    return;
  }
  ExecutionAnswer ans;
  ans.id = req.id;
  std::string error_msg;
  ans.status = sb->Execute(req.options, &ans.info, &error_msg);
  if (error_msg.size() >= 8192) throw std::runtime_error("string too long");
  strcpy(ans.error_msg, error_msg.c_str());
  answers->Enqueue(ans);
}

void Manager() {
  signal(SIGTERM, SIG_IGN);
  signal(SIGINT, SIG_IGN);
  signal(SIGQUIT, SIG_IGN);
  signal(SIGHUP, SIG_IGN);
  int parentfd = pipefd[0];
  int flags = fcntl(parentfd, F_GETFL, 0);
  fcntl(parentfd, F_SETFL, flags | O_NONBLOCK);
  size_t num_boxes = std::thread::hardware_concurrency();
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
        Sandbox();
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
  requests->Stop();
  answers->Stop();
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

void SandboxManager::Start() {
  // Create communication queues
  requests = std::make_unique<std::decay_t<decltype(*requests)>>(queue_size);
  answers = std::make_unique<std::decay_t<decltype(*answers)>>(queue_size);

  // Create pipe for communication with the sandbox manager
  check_error(pipe(pipefd));

  // Start the Manager process
  pid_t pid;
  check_error(pid = fork());
  if (pid == 0) {
    close(pipefd[1]);
    Manager();
    _Exit(0);
  } else {
    close(pipefd[0]);
    // Ignore SIGCHLD so that the manager can die later than us
    signal(SIGCHLD, SIG_IGN);
    response_receiver = std::thread(ResponseReceiver);
  }
}

void SandboxManager::Stop() {
  requests->Stop();
  answers->Stop();
  response_receiver.join();
}

void SandboxManager::ChangeNumBoxes(size_t num) {
  check_error(write(pipefd[1], &num, sizeof(num)));
}

bool SandboxManager::Execute(const ExecutionOptions& options,
                             ExecutionInfo* info, std::string* error_msg) {
  size_t id = next_id++;
  ExecutionRequest req{id, options};
  if (!requests->Enqueue(req)) {
    throw std::runtime_error("Sandbox execution request after exit!");
  }
  std::unique_lock<std::mutex> lck(received_answers_mutex);
  while (!received_answers.count(id)) {
    received_answers_cv.wait(lck);
  }
  memcpy(info, &received_answers[id].info, sizeof(ExecutionInfo));
  *error_msg = received_answers[id].error_msg;
  return received_answers[id].status;
}

}  // namespace sandbox
