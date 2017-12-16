#include <future>
#include <iostream>
#include <queue>
#include <string>

#include "gflags/gflags.h"
#include "grpc++/security/server_credentials.h"
#include "grpc++/server.h"
#include "grpc++/server_builder.h"
#include "grpc++/server_context.h"
#include "grpc/grpc.h"
#include "proto/server.grpc.pb.h"
#include "util/file.hpp"
#include "util/flags.hpp"

DEFINE_string(address, "0.0.0.0", "address to listen on");
DEFINE_int32(port, 7070, "port to listen on");

class TaskMakerServerImpl : public proto::TaskMakerServer::Service {
 public:
  TaskMakerServerImpl(const std::string& store_dir) {
    util::File::MakeDirs(store_dir);
  }

  grpc::Status SendFile(grpc::ServerContext* context,
                        grpc::ServerReader<proto::FileContents>* reader,
                        proto::SendFileResponse* response) override {
    proto::FileContents contents;
    reader->Read(&contents);
    if (!contents.has_hash()) {
      std::cerr << "SendFile without hash" << std::endl;
      return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT,
                          "No hash provided");
    }
    std::string path = util::File::ProtoSHAToPath(contents.hash());
    std::cerr << "Receiving file " << path << std::endl;
    if (util::File::Size(path) >= 0)
      return grpc::Status(grpc::StatusCode::ALREADY_EXISTS, "File exists");
    try {
      util::File::Write(
          path, [&contents,
                 &reader](const util::File::ChunkReceiver& chunk_receiver) {
            do {
              std::cerr << "Received chunk" << std::endl;
              chunk_receiver(contents);
            } while (reader->Read(&contents));
            if (!contents.last()) {
              throw std::runtime_error("Connection closed unexpectedly");
            }
          });
      std::cerr << "Saved file " << path << std::endl;
      return grpc::Status::OK;
    } catch (std::exception& e) {
      std::cerr << "SendFile: " << e.what() << std::endl;
      return grpc::Status(grpc::StatusCode::UNKNOWN, e.what());
    }
  }

  grpc::Status RetrieveFile(
      grpc::ServerContext* context, const proto::SHA256* hash,
      grpc::ServerWriter<proto::FileContents>* writer) override {
    std::string path = util::File::ProtoSHAToPath(*hash);
    std::cerr << "Ask for file " << path << std::endl;
    try {
      util::File::Read(path, [&writer](const proto::FileContents& contents) {
        writer->Write(contents);
      });
      return grpc::Status::OK;
    } catch (std::system_error& e) {
      if (e.code().value() ==
          static_cast<int>(std::errc::no_such_file_or_directory))
        return grpc::Status(grpc::StatusCode::NOT_FOUND, path);
      std::cerr << "RetrieveFile: " << e.what() << std::endl;
      return grpc::Status(grpc::StatusCode::UNKNOWN, e.what());
    } catch (std::exception& e) {
      std::cerr << "RetrieveFile: " << e.what() << std::endl;
      return grpc::Status(grpc::StatusCode::UNKNOWN, e.what());
    }
  }

  grpc::Status Execute(grpc::ServerContext* context,
                       const proto::Request* request,
                       proto::Response* response) override {
    for (int i = 0; i < max_attempts; i++) {
      PendingRequest pending_request;
      pending_request.request = *request;
      std::cerr << "Execute attempt " << (i + 1) << " " << request->executable()
                << std::endl;
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
          std::cerr << "Error on worker: " << response->error_message()
                    << std::endl;
          continue;
        }
        break;
      } catch (std::future_error& e) {
        if (i + 1 == max_attempts) {
          std::cerr << "Execute failed: " << e.what() << std::endl;
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
    std::cerr << "Worker " << name << " connected" << std::endl;
    while (true) {
      std::unique_lock<std::mutex> lck(requests_mutex_);
      while (pending_requests_.empty()) {
        request_available_.wait(lck);
      }
      PendingRequest pending_request = std::move(pending_requests_.front());
      pending_requests_.pop();
      lck.unlock();
      std::cerr << "Sent work to worker" << name << ": "
                << pending_request.request.executable() << std::endl;
      if (!stream->Write(pending_request.request)) {
        std::unique_lock<std::mutex> lck(requests_mutex_);
        pending_requests_.push(std::move(pending_request));
        request_available_.notify_all();
        break;
      }
      proto::Response response;
      if (!stream->Read(&response)) {
        std::cerr << "Worker " << name << " did not answer" << std::endl;
        return grpc::Status(grpc::StatusCode::UNAVAILABLE,
                            "Worker did not answer");
      }
      std::cerr << "Worker " << name << " done" << std::endl;
      pending_request.response.set_value(response);
    }
    std::cerr << "Worker " << name << " disconnected" << std::endl;
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
};

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  std::string server_address = FLAGS_address + ":" + std::to_string(FLAGS_port);
  TaskMakerServerImpl service(FLAGS_store_directory);
  grpc::ServerBuilder builder;
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  builder.RegisterService(&service);
  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  std::cout << "Server listening on " << server_address << std::endl;
  server->Wait();
}
