#include <condition_variable>

#include "absl/memory/memory.h"
#include "absl/types/optional.h"
#include "core/core.hpp"
#include "event_queue.hpp"
#include "gflags/gflags.h"
#include "glog/logging.h"
#include "grpc++/security/server_credentials.h"
#include "grpc++/server.h"
#include "grpc++/server_builder.h"
#include "grpc++/server_context.h"
#include "manager/ioi_evaluation.hpp"
#include "manager/terry_evaluation.hpp"
#include "proto/manager.grpc.pb.h"

DEFINE_int32(port, 7071, "port to listen on");  // NOLINT

namespace {
const auto RUNNING_TASK_POLL_INTERVAL = std::chrono::seconds(1);  // NOLINT
}  // namespace

class TaskMakerManagerImpl : public proto::TaskMakerManager::Service {
 public:
  grpc::Status EvaluateTask(grpc::ServerContext* /*context*/,
                            const proto::EvaluateTaskRequest* request,
                            grpc::ServerWriter<proto::Event>* writer) override {
    std::lock_guard<std::mutex> lck(requests_mutex_);

    int64_t current_id = evaluation_id_counter_++;
    EvaluationInfo info = setup_request(*request);

    running_[current_id] = std::move(info);
    run_core(*request, current_id);

    return process_request(current_id, writer);
  }
  grpc::Status EvaluateTerryTask(
      grpc::ServerContext* /*context*/,
      const proto::EvaluateTerryTaskRequest* request,
      grpc::ServerWriter<proto::Event>* writer) override {
    std::lock_guard<std::mutex> lck(requests_mutex_);

    int64_t current_id = evaluation_id_counter_++;
    EvaluationInfo info = setup_request(*request);

    running_[current_id] = std::move(info);
    run_core(*request, current_id);

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
    // TODO(edomora97) eventually kill the core/thread
    // FIXME it doesn't work :(
    LOG(WARNING) << "Requesting to shutdown the server";
    if (request->force()) {
      LOG(WARNING) << " -- FORCING SHUTDOWN --";
      for (auto& kw : running_) {
        kw.second.core->Stop();
        kw.second.queue->Stop();
      }
    }
    for (auto& kw : running_) {
      kw.second.running_thread.join();
    }
    server_->Shutdown();
    return grpc::Status(grpc::StatusCode::UNIMPLEMENTED, "TODO");
  }

  void RegisterServer(grpc::Server* server) { server_ = server; }

 private:
  struct EvaluationInfo {
    std::unique_ptr<core::Core> core;
    std::unique_ptr<manager::EventQueue> queue;
    std::unique_ptr<manager::Generation> generation;
    std::unique_ptr<manager::Evaluation> evaluation;
    std::map<std::string, std::unique_ptr<manager::SourceFile>> source_files;

    std::thread running_thread;
  };

  grpc::Server* server_ = nullptr;
  std::map<int64_t, EvaluationInfo> running_ GUARDED_BY(requests_mutex_);
  int64_t evaluation_id_counter_ = 0;
  std::mutex requests_mutex_;

  EvaluationInfo setup_request(const proto::EvaluateTaskRequest& request) {
    EvaluationInfo info{};
    info.core = absl::make_unique<core::Core>();
    info.core->SetStoreDirectory(request.store_dir());
    info.core->SetTempDirectory(request.temp_dir());
    info.core->SetNumCores(request.num_cores());

    info.queue = absl::make_unique<manager::EventQueue>();

    info.generation = absl::make_unique<manager::IOIGeneration>(
        info.queue.get(), info.core.get(), request.task(), request.cache_mode(),
        request.evaluate_on(), request.keep_sandbox());

    info.evaluation = absl::make_unique<manager::IOIEvaluation>(
        info.queue.get(), info.core.get(),
        reinterpret_cast<manager::IOIGeneration*>(info.generation.get()),
        request.task(), request.exclusive(), request.cache_mode(),
        request.evaluate_on(), request.keep_sandbox());

    std::map<proto::Language, proto::GraderInfo> graders;
    for (const proto::GraderInfo& grader : request.task().grader_info())
      graders[grader.for_language()] = grader;

    for (const proto::SourceFile& source : request.solutions()) {
      absl::optional<proto::GraderInfo> grader;
      if (graders.count(source.language()) == 1)
        grader = graders[source.language()];
      info.source_files[source.path()] = manager::SourceFile::FromProto(
          info.queue.get(), info.core.get(), source, grader, false,
          request.keep_sandbox());
      auto* evaluation =
          reinterpret_cast<manager::IOIEvaluation*>(info.evaluation.get());
      evaluation->Evaluate(info.source_files[source.path()].get());
    }

    return info;
  }

  EvaluationInfo setup_request(const proto::EvaluateTerryTaskRequest& request) {
    EvaluationInfo info{};
    info.core = absl::make_unique<core::Core>();
    info.core->SetStoreDirectory(request.store_dir());
    info.core->SetTempDirectory(request.temp_dir());
    info.core->SetNumCores(request.num_cores());

    info.queue = absl::make_unique<manager::EventQueue>();

    info.generation = absl::make_unique<manager::TerryGeneration>(
        info.queue.get(), info.core.get(), request.task(), request.cache_mode(),
        request.evaluate_on(), request.keep_sandbox());
    info.evaluation = absl::make_unique<manager::TerryEvaluation>(
        info.queue.get(), info.core.get(),
        reinterpret_cast<manager::TerryGeneration*>(info.generation.get()),
        request.task(), request.cache_mode(), request.evaluate_on(),
        request.keep_sandbox());

    for (const proto::SourceFile& source : request.solutions()) {
      info.source_files[source.path()] = manager::SourceFile::FromProto(
          info.queue.get(), info.core.get(), source, {}, false,
          request.keep_sandbox());
      auto* evaluation =
          reinterpret_cast<manager::TerryEvaluation*>(info.evaluation.get());
      evaluation->Evaluate(info.source_files[source.path()].get());
    }

    return info;
  }

  void run_core(const proto::EvaluateTaskRequest& request, int64_t current_id) {
    running_[current_id].running_thread = std::thread([this, request,
                                                       current_id] {
      EvaluationInfo& info = running_[current_id];
      LOG(INFO) << "Starting new core for request " << current_id;
      try {
        if (info.core->Run()) {
          LOG(INFO) << "The core for request " << current_id
                    << " has succeeded";
          info.queue->Stop();
          if (request.dry_run()) {
            LOG(INFO) << "Dry-run mode, inputs/outputs/checker not saved";
            return;
          }
          auto* generation =
              reinterpret_cast<manager::IOIGeneration*>(info.generation.get());
          if (request.task().has_checker() &&
              !request.write_checker_to().empty())
            generation->WriteChecker(request);
          generation->WriteInputs(request);
          generation->WriteOutputs(request);
        } else {
          info.queue->FatalError("The core failed!");
          LOG(WARNING) << "The core for request " << current_id
                       << " has failed";
          info.queue->Stop();
        }
      } catch (const std::exception& ex) {
        LOG(WARNING) << "The core for request " << current_id
                     << " has failed with an excetpion: " << ex.what();
        info.queue->FatalError(std::string("The core failed! ") + ex.what());
        info.queue->Stop();
      }
    });
  }

  void run_core(const proto::EvaluateTerryTaskRequest& request,
                int64_t current_id) {
    running_[current_id].running_thread = std::thread([this, request,
                                                       current_id] {
      EvaluationInfo& info = running_[current_id];
      LOG(INFO) << "Starting new core for terry request " << current_id;
      try {
        if (info.core->Run()) {
          LOG(INFO) << "The core for request " << current_id
                    << " has succeeded";
          info.queue->Stop();
          if (request.dry_run()) {
            LOG(INFO) << "Dry-run mode, compiled files not saved";
            return;
          }
          auto* generation =
              reinterpret_cast<manager::TerryGeneration*>(
                  info.generation.get());
          generation->WriteGenerator(request);
          generation->WriteChecker(request);
          if (request.task().has_validator())
            generation->WriteValidator(request);
        } else {
          info.queue->FatalError("The core failed");
          LOG(WARNING) << "The core for request " << current_id
                       << " has failed";
          info.queue->Stop();
        }
      } catch (const std::exception& ex) {
        LOG(WARNING) << "The core for request " << current_id
                     << " has failed with exception: " << ex.what();
        info.queue->FatalError(std::string("The core failed! ") + ex.what());
        info.queue->Stop();
      }
    });
  }

  grpc::Status process_request(int64_t current_id,
                               grpc::ServerWriter<proto::Event>* writer) {
    manager::EventQueue* queue = running_[current_id].queue.get();
    absl::optional<proto::Event> event;

    std::mutex writer_mutex;
    // send EvaluationStarted event
    {
      std::lock_guard<std::mutex> lock(writer_mutex);
      proto::Event eval_started_event;
      auto* sub_event = eval_started_event.mutable_evaluation_started();
      sub_event->set_id(current_id);
      writer->Write(eval_started_event);
    }
    // running is true while the core has not finished, this is synchronized for
    // the poller thread
    bool running = true;
    std::condition_variable running_cv;
    std::mutex running_mutex;

    // every RUNNING_TASK_POLL_INTERVAL get the list of running tasks from the
    // core
    std::thread poller([&running, &running_cv, &running_mutex, queue,
                        current_id, writer, &writer_mutex, this] {
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
          std::lock_guard<std::mutex> lock(writer_mutex);
          writer->Write(event);
        }
        running_cv.wait_for(lck, RUNNING_TASK_POLL_INTERVAL);
      }
    });
    // forward all the events from the event queue
    while ((event = queue->Dequeue())) {
      std::lock_guard<std::mutex> lock(writer_mutex);
      writer->Write(*event);
    }
    // send EvaluationEnded event
    {
      std::lock_guard<std::mutex> lock(writer_mutex);
      proto::Event eval_ended_event;
      auto* sub_event = eval_ended_event.mutable_evaluation_ended();
      sub_event->set_id(current_id);
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

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);  // NOLINT
  google::InstallFailureSignalHandler();

  std::string server_address = "127.0.0.1:" + std::to_string(FLAGS_port);
  TaskMakerManagerImpl service;
  grpc::ServerBuilder builder;
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  builder.RegisterService(&service);
  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  service.RegisterServer(server.get());
  LOG(INFO) << "Server listening on " << server_address;
  server->Wait();
}
