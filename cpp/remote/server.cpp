#include <future>
#include <queue>

#include "plog/Log.h"
#include "grpc++/security/server_credentials.h"
#include "grpc++/server.h"
#include "grpc++/server_builder.h"
#include "grpc++/server_context.h"
#include "proto/server.grpc.pb.h"
#include "util/file.hpp"
#include "util/flags.hpp"

class TaskMakerServerImpl : public proto::TaskMakerServer::Service {
 public:
  explicit TaskMakerServerImpl(const std::string& store_dir)
      : store_directory_(store_dir) {
    util::File::MakeDirs(store_dir);
  }

  grpc::Status SendFile(grpc::ServerContext* /*context*/,
                        grpc::ServerReader<proto::FileContents>* reader,
                        proto::SendFileResponse* /*response*/) override {
    proto::FileContents contents;
    reader->Read(&contents);
    if (!contents.has_hash()) {
      LOGE << "SendFile without hash";
      return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT,
                          "No hash provided");
    }
    std::string path =
        util::File::ProtoSHAToPath(store_directory_, contents.hash());
    LOGI << "Receiving file " << path;
    if (util::File::Size(path) >= 0)
      return grpc::Status(grpc::StatusCode::ALREADY_EXISTS, "File exists");
    try {
      util::File::Write(
          path, [&contents,
                 &reader](const util::File::ChunkReceiver& chunk_receiver) {
            do {
              LOGI << "Received chunk";
              chunk_receiver(contents);
            } while (reader->Read(&contents));
            if (!contents.last()) {
              throw std::runtime_error("Connection closed unexpectedly");
            }
          });
      LOGI << "Saved file " << path;
      return grpc::Status::OK;
    } catch (std::exception& e) {
      LOGE << "SendFile: " << e.what();
      return grpc::Status(grpc::StatusCode::UNKNOWN, e.what());
    }
  }

  grpc::Status RetrieveFile(
      grpc::ServerContext* /*context*/, const proto::SHA256* hash,
      grpc::ServerWriter<proto::FileContents>* writer) override {
    std::string path = util::File::ProtoSHAToPath(store_directory_, *hash);
    LOGI << "Ask for file " << path;
    try {
      util::File::Read(path, [&writer](const proto::FileContents& contents) {
        writer->Write(contents);
      });
      LOGI << "Sent file " << path;
      return grpc::Status::OK;
    } catch (std::system_error& e) {
      if (e.code().value() ==
          static_cast<int>(std::errc::no_such_file_or_directory))
        return grpc::Status(grpc::StatusCode::NOT_FOUND, path);
      LOGE << "RetrieveFile: " << e.what();
      return grpc::Status(grpc::StatusCode::UNKNOWN, e.what());
    } catch (std::exception& e) {
      LOGE << "RetrieveFile: " << e.what();
      return grpc::Status(grpc::StatusCode::UNKNOWN, e.what());
    }
  }

  grpc::Status Execute(grpc::ServerContext* /*context*/,
                       const proto::Request* request,
                       proto::Response* response) override {
    for (int i = 0; i < max_attempts; i++) {
      PendingRequest pending_request;
      pending_request.request = *request;
      LOGI << "Execute attempt " << (i + 1) << " "
                << request->executable();
      std::future<proto::Response> response_future =
          pending_request.response.get_future();
      {
        std::unique_lock<std::mutex> lck(requests_mutex_);
        pending_requests_.push(std::move(pending_request));
        request_available_.notify_all();
      }
      try {
        *response = response_future.get();
        if (response->status() == proto::Status::INTERNAL_ERROR &&
            i + 1 < max_attempts) {
          LOGE << "Error on worker: " << response->error_message();
          continue;
        }
        break;
      } catch (std::future_error& e) {
        if (i + 1 == max_attempts) {
          LOGE << "Execute failed: " << e.what();
          return grpc::Status(grpc::StatusCode::UNAVAILABLE, e.what());
        }
      }
    }
    return grpc::Status::OK;
  }

  grpc::Status GetWork(
      grpc::ServerContext* context,
      grpc::ServerReaderWriter<proto::Request, proto::Response>* stream)
      override {
    std::string name;
    for (const auto& kv : context->client_metadata()) {
      if (kv.first == "name") {
        name = std::string(kv.second.data(), kv.second.length());
      }
    }
    LOGI << "Worker " << name << " connected";
    while (true) {
      std::unique_lock<std::mutex> lck(requests_mutex_);
      while (pending_requests_.empty()) {
        request_available_.wait(lck);
      }
      PendingRequest pending_request = std::move(pending_requests_.front());
      pending_requests_.pop();
      lck.unlock();
      LOGI << "Sent work to worker" << name << ": "
                << pending_request.request.executable();
      if (!stream->Write(pending_request.request)) {
        std::unique_lock<std::mutex> lck(requests_mutex_);
        pending_requests_.push(std::move(pending_request));
        request_available_.notify_all();
        break;
      }
      proto::Response response;
      if (!stream->Read(&response)) {
        LOGE << "Worker " << name << " did not answer";
        return grpc::Status(grpc::StatusCode::UNAVAILABLE,
                            "Worker did not answer");
      }
      LOGI << "Worker " << name << " done";
      pending_request.response.set_value(response);
    }
    LOGW << "Worker " << name << " disconnected";
    return grpc::Status(grpc::StatusCode::UNAVAILABLE, "Worker disconnected");
  }

 private:
  struct PendingRequest {
    proto::Request request;
    std::promise<proto::Response> response;
  };
  static const constexpr int max_attempts = 4;
  std::mutex requests_mutex_;
  std::condition_variable request_available_;
  std::queue<PendingRequest> pending_requests_;
  std::string store_directory_;
};

int server_main() {
  std::string server_address = FLAGS_address + ":" + std::to_string(FLAGS_server_port);
  TaskMakerServerImpl service(FLAGS_store_directory);
  grpc::ServerBuilder builder;
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  builder.RegisterService(&service);
  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  std::cout << "Server listening on " << server_address << std::endl;
  server->Wait();
  return 0;
}
