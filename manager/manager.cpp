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

DEFINE_string(address, "0.0.0.0", "adress to listen on");
DEFINE_int32(port, 7071, "port to listen on");

class TaskMakerManagerImpl : public proto::TaskMakerManager::Service {
 public:
  grpc::Status EvaluateTask(grpc::ServerContext* context,
                            const proto::EvaluateTaskRequest* request,
                            proto::EvaluateTaskResponse* response) override {
    std::unique_lock<std::mutex> lck(requests_mutex_);
    int64_t current_id = evaluation_id_counter_++;
    EvaluationInfo info{};
    info.core = absl::make_unique<core::Core>();
    info.core->SetStoreDirectory(request->store_dir());
    info.core->SetTempDirectory(request->temp_dir());
    info.core->SetNumCores(request->num_cores());

    info.queue = absl::make_unique<manager::EventQueue>();

    info.generation = absl::make_unique<manager::Generation>(
        info.queue.get(), info.core.get(), request->task(),
        request->cache_mode(), request->evaluate_on());

    info.evaluation = absl::make_unique<manager::Evaluation>(
        info.queue.get(), info.core.get(), *info.generation, request->task(),
        request->exclusive(), request->cache_mode(), request->evaluate_on());

    std::map<proto::Language, proto::GraderInfo> graders;
    for (proto::GraderInfo grader : request->task().grader_info())
      graders[grader.for_language()] = grader;

    for (proto::SourceFile source : request->solutions()) {
      absl::optional<proto::GraderInfo> grader;
      if (graders.count(source.language()) == 1)
        grader = graders[source.language()];
      info.source_files[source.path()] = manager::SourceFile::FromProto(
          info.queue.get(), info.core.get(), source, grader, false);
      info.evaluation->Evaluate(info.source_files[source.path()].get());
    }

    // TODO maybe we want a queue and run a core at a time?
    proto::EvaluateTaskRequest req;
    req.CopyFrom(*request);
    info.running_thread = std::thread([this, req, current_id] {
      auto& info = running_[current_id];
      LOG(INFO) << "Starting new core for request " << current_id;
      if (info.core->Run()) {
        LOG(INFO) << "The core for request " << current_id << " has succeeded";
        info.queue->Stop();
        if (req.dry_run()) return;
        if (req.task().has_checker() && !req.write_checker_to().empty())
          info.generation->WriteChecker(req);
        info.generation->WriteInputs(req);
        info.generation->WriteOutputs(req);
      } else {
        // TODO manage the core failure
        info.queue->FatalError("The core failed!");
        LOG(WARNING) << "The core for request " << current_id << " has failed";
      }
    });

    running_[current_id] = std::move(info);
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
    while (event = queue->Dequeue()) writer->Write(*event);

    // if the queue is empty and stopped we can safely remove the request
    if (queue->IsStopped()) {
      running_[running_id].running_thread.join();
      running_.erase(running_id);
    }
    LOG(INFO) << "Deallocated request " << running_id;
    return grpc::Status::OK;
  }
  grpc::Status Stop(grpc::ServerContext* context,
                    const proto::StopRequest* request,
                    proto::StopResponse* response) override {
    int64_t request_id = request->evaluation_id();
    LOG(WARNING) << "Requesting to stop request " << request_id;
    // TODO we need core.Stop() and/or core.Kill()
    return grpc::Status(grpc::StatusCode::UNIMPLEMENTED, "TODO");
  }
  grpc::Status Shutdown(grpc::ServerContext* context,
                        const proto::ShutdownRequest* request,
                        proto::ShutdownResponse* response) override {
    LOG(WARNING) << "Requesting to shutdown the server";
    if (request->force())
      LOG(WARNING) << " -- FORCING SHUTDOWN --";
    // TODO eventually kill the core/thread
    // TODO we need core.Stop() and/or core.Kill()
    for (auto& kw : running_) kw.second.running_thread.join();
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
};

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  google::InitGoogleLogging(argv[0]);
  google::InstallFailureSignalHandler();

  std::string server_address = FLAGS_address + ":" + std::to_string(FLAGS_port);
  TaskMakerManagerImpl service;
  grpc::ServerBuilder builder;
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  builder.RegisterService(&service);
  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  service.RegisterServer(server.get());
  LOG(INFO) << "Server listening on " << server_address;
  server->Wait();
}
