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
#include "manager/evaluation.hpp"
#include "proto/manager.grpc.pb.h"

DEFINE_int32(port, 7071, "port to listen on");

class TaskMakerManagerImpl : public proto::TaskMakerManager::Service {
 public:
  grpc::Status EvaluateTask(grpc::ServerContext* context,
                            const proto::EvaluateTaskRequest* request,
                            proto::EvaluateTaskResponse* response) override {
    // TODO(edomora97) push an event to the queue when the lock is blocked
    // TODO(veluca93): change this to something sane.
    LOG(INFO) << request->DebugString();
    requests_mutex_.lock();
    int64_t current_id = evaluation_id_counter_++;
    EvaluationInfo info = setup_request(*request);

    running_[current_id] = std::move(info);
    run_core(*request, current_id);
    response->set_id(current_id);
    return grpc::Status::OK;
  }
  grpc::Status GetEvents(grpc::ServerContext* context,
                         const proto::GetEventsRequest* request,
                         grpc::ServerWriter<proto::Event>* writer) override {
    int64_t running_id = request->evaluation_id();
    if (running_.count(running_id) == 0)
      return grpc::Status(grpc::StatusCode::NOT_FOUND, "No such id");

    manager::EventQueue* queue = running_[running_id].queue.get();
    absl::optional<proto::Event> event;
    while ((event = queue->Dequeue())) {
      writer->Write(*event);
    }

    // if the queue is empty and stopped we can safely remove the request
    if (queue->IsStopped()) {
      running_[running_id].running_thread.join();
      running_.erase(running_id);
    }
    requests_mutex_.unlock();
    LOG(INFO) << "Deallocated request " << running_id;
    return grpc::Status::OK;
  }
  grpc::Status Stop(grpc::ServerContext* context,
                    const proto::StopRequest* request,
                    proto::StopResponse* response) override {
    int64_t request_id = request->evaluation_id();
    if (running_.count(request_id) == 0)
      return grpc::Status(grpc::StatusCode::NOT_FOUND, "No such id");

    LOG(WARNING) << "Requesting to stop request " << request_id;
    running_[request_id].core->Stop();
    running_[request_id].queue->Stop();
    return grpc::Status::OK;
  }
  grpc::Status Shutdown(grpc::ServerContext* context,
                        const proto::ShutdownRequest* request,
                        proto::ShutdownResponse* response) override {
    // TODO eventually kill the core/thread
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
  std::map<int64_t, EvaluationInfo> running_{};
  int64_t evaluation_id_counter_ = 0;
  std::mutex requests_mutex_;

  EvaluationInfo setup_request(proto::EvaluateTaskRequest request) {
    EvaluationInfo info{};
    info.core = absl::make_unique<core::Core>();
    info.core->SetStoreDirectory(request.store_dir());
    info.core->SetTempDirectory(request.temp_dir());
    info.core->SetNumCores(request.num_cores());

    info.queue = absl::make_unique<manager::EventQueue>();

    info.generation = absl::make_unique<manager::Generation>(
        info.queue.get(), info.core.get(), request.task(), request.cache_mode(),
        request.evaluate_on());

    info.evaluation = absl::make_unique<manager::Evaluation>(
        info.queue.get(), info.core.get(), *info.generation, request.task(),
        request.exclusive(), request.cache_mode(), request.evaluate_on());

    std::map<proto::Language, proto::GraderInfo> graders;
    for (proto::GraderInfo grader : request.task().grader_info())
      graders[grader.for_language()] = grader;

    for (proto::SourceFile source : request.solutions()) {
      absl::optional<proto::GraderInfo> grader;
      if (graders.count(source.language()) == 1)
        grader = graders[source.language()];
      info.source_files[source.path()] = manager::SourceFile::FromProto(
          info.queue.get(), info.core.get(), source, grader, false);
      info.evaluation->Evaluate(info.source_files[source.path()].get());
    }

    return info;
  }

  void run_core(proto::EvaluateTaskRequest request, int64_t current_id) {
    EvaluationInfo& info = running_[current_id];
    info.running_thread = std::thread([this, request, current_id] {
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
          if (request.task().has_checker() &&
              !request.write_checker_to().empty())
            info.generation->WriteChecker(request);
          info.generation->WriteInputs(request);
          info.generation->WriteOutputs(request);
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
};

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);
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
