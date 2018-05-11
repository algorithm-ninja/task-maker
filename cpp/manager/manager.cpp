#include <condition_variable>
#include <future>

#include "core/core.hpp"
#include "event_queue.hpp"
#include "gflags/gflags.h"
#include "glog/logging.h"
#include "grpc++/security/server_credentials.h"
#include "grpc++/server.h"
#include "grpc++/server_builder.h"
#include "grpc++/server_context.h"
#include "manager/evaluation_info.hpp"
#include "manager/ioi_format/ioi_format.hpp"
#include "manager/terry_format/terry_format.hpp"
#include "proto/manager.grpc.pb.h"

DEFINE_int32(port, 7071, "port to listen on");  // NOLINT

namespace {
const auto RUNNING_TASK_POLL_INTERVAL = std::chrono::seconds(1);  // NOLINT

// will be resolved if a shutdown request is made
std::promise<void> do_exit;
}  // namespace

namespace manager {
class TaskMakerManagerImpl : public proto::TaskMakerManager::Service {
 public:
  grpc::Status EvaluateTask(grpc::ServerContext* /*context*/,
                            const proto::EvaluateTaskRequest* request,
                            grpc::ServerWriter<proto::Event>* writer) override {
    std::lock_guard<std::mutex> lck(requests_mutex_);
    VLOG(3) << request->DebugString();

    int64_t current_id = evaluation_id_counter_++;
    EvaluationInfo info = manager::setup_request(*request);

    if (info.queue->IsStopped()) {
      info.queue->BindWriterUnlocked(writer);
      LOG(ERROR) << "Deleted request " << current_id;
      return grpc::Status::OK;
    }

    running_[current_id] = std::move(info);
    manager::run_core(*request, current_id, &running_);

    return process_request(current_id, writer);
  }
  grpc::Status EvaluateTerryTask(
      grpc::ServerContext* /*context*/,
      const proto::EvaluateTerryTaskRequest* request,
      grpc::ServerWriter<proto::Event>* writer) override {
    std::lock_guard<std::mutex> lck(requests_mutex_);
    VLOG(3) << request->DebugString();

    int64_t current_id = evaluation_id_counter_++;
    EvaluationInfo info = manager::setup_request(*request);

    if (info.queue->IsStopped()) {
      info.queue->BindWriterUnlocked(writer);
      LOG(ERROR) << "Deleted request " << current_id;
      return grpc::Status::OK;
    }

    running_[current_id] = std::move(info);
    manager::run_core(*request, current_id, &running_);

    return process_request(current_id, writer);
  }
  grpc::Status CleanTask(grpc::ServerContext* /*context*/,
                         const proto::CleanTaskRequest* request,
                         proto::CleanTaskResponse* /*response*/) override {
    LOG(INFO) << "Cleaning task directories:\n"
              << "\t" << request->store_dir() << "\n"
              << "\t" << request->temp_dir();
    try {
      util::File::RemoveTree(request->store_dir());
    } catch (const std::system_error&) {
    }
    try {
      util::File::RemoveTree(request->temp_dir());
    } catch (const std::system_error&) {
    }
    return grpc::Status::OK;
  }
  grpc::Status Stop(grpc::ServerContext* /*context*/,
                    const proto::StopRequest* request,
                    proto::StopResponse* /*response*/) override {
    int64_t request_id = request->evaluation_id();
    if (running_.count(request_id) == 0)
      return grpc::Status(grpc::StatusCode::NOT_FOUND, "No such id");

    LOG(WARNING) << "Requesting to stop request " << request_id;
    running_[request_id].core->Stop();
    running_[request_id].queue->Stop();
    return grpc::Status::OK;
  }
  grpc::Status Shutdown(grpc::ServerContext* /*context*/,
                        const proto::ShutdownRequest* request,
                        proto::ShutdownResponse* /*response*/) override {
    LOG(WARNING) << "Requesting to shutdown the server";
    if (!running_.empty()) LOG(WARNING) << "There is an execution running";
    if (request->force()) {
      LOG(WARNING) << " -- FORCING SHUTDOWN --";
      for (auto& kw : running_) {
        if (kw.second.is_remote)
          return grpc::Status(grpc::StatusCode::FAILED_PRECONDITION,
                              "Not forcing remote execution killing");
        kw.second.core->Stop();
        kw.second.queue->Stop();
      }
    }
    std::lock_guard<std::mutex> lck(requests_mutex_);
    for (auto& kw : running_) kw.second.running_thread.join();
    do_exit.set_value();
    return grpc::Status::OK;
  }

  void RegisterServer(grpc::Server* server) { server_ = server; }

 private:
  grpc::Server* server_ = nullptr;
  std::map<int64_t, EvaluationInfo> running_;
  int64_t evaluation_id_counter_ = 0;
  std::mutex requests_mutex_;

  grpc::Status process_request(int64_t current_id,
                               grpc::ServerWriter<proto::Event>* writer) {
    manager::EventQueue* queue = running_[current_id].queue.get();

    std::mutex writer_mutex;
    // send EvaluationStarted event
    {
      proto::Event eval_started_event;
      auto* sub_event = eval_started_event.mutable_evaluation_started();
      sub_event->set_id(current_id);
      queue->Enqueue(std::move(eval_started_event));
    }
    // running is true while the core has not finished, this is synchronized for
    // the poller thread
    bool running = true;
    std::condition_variable running_cv;
    std::mutex running_mutex;

    // every RUNNING_TASK_POLL_INTERVAL get the list of running tasks from the
    // core
    std::thread poller([&running, &running_cv, &running_mutex, current_id,
                        writer, &writer_mutex, this] {
      std::unique_lock<std::mutex> lck(running_mutex);
      while (running) {
        core::Core* core = running_[current_id].core.get();
        std::vector<core::RunningTaskInfo> tasks = core->RunningTasks();
        proto::Event event;
        auto* sub_event = event.mutable_running_tasks();
        auto now = std::chrono::system_clock::now();
        for (const core::RunningTaskInfo& task : tasks) {
          auto* event_task = sub_event->add_task();
          std::chrono::duration<float> duration = now - task.started;
          event_task->set_description(task.description);
          event_task->set_duration(duration.count());
        }
        {
          // we cannot push this to the queue because in this thread the queue
          // may has been closed
          std::lock_guard<std::mutex> lock(writer_mutex);
          writer->Write(event);
        }
        running_cv.wait_for(lck, RUNNING_TASK_POLL_INTERVAL);
      }
    });
    // forward all the events from the event queue
    queue->BindWriter(writer, &writer_mutex);
    // send EvaluationEnded event
    {
      std::lock_guard<std::mutex> lock(writer_mutex);
      proto::Event eval_ended_event;
      auto* sub_event = eval_ended_event.mutable_evaluation_ended();
      sub_event->set_id(current_id);
      // the queue has ended so we cannot push with it
      writer->Write(eval_ended_event);
    }
    // stop the poller thread
    {
      std::lock_guard<std::mutex> lock(running_mutex);
      running = false;
    }
    running_cv.notify_all();
    poller.join();

    // if the queue is empty and stopped we can safely remove the request
    CHECK(queue->IsStopped()) << "Core exited but the queue is not stopped";
    running_[current_id].running_thread.join();
    running_.erase(current_id);
    LOG(INFO) << "Deallocated request " << current_id;
    return grpc::Status::OK;
  }
};
}  // namespace manager

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);  // NOLINT
  google::InstallFailureSignalHandler();

  std::string server_address = "127.0.0.1:" + std::to_string(FLAGS_port);
  manager::TaskMakerManagerImpl service;
  grpc::ServerBuilder builder;
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  builder.RegisterService(&service);
  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  service.RegisterServer(server.get());
  LOG(INFO) << "Server listening on " << server_address;
  std::thread serving_thread([&]() { server->Wait(); });
  do_exit.get_future().wait();
  LOG(WARNING) << "Shutting down the server, goodbye";
  server->Shutdown();
  serving_thread.join();
}
