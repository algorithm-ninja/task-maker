#include <functional>
#include <memory>
#include <thread>
#include <vector>

#include "executor/local_executor.hpp"
#include "gflags/gflags.h"
#include "glog/logging.h"
#include "grpc++/channel.h"
#include "grpc++/create_channel.h"
#include "proto/server.grpc.pb.h"
#include "remote/common.hpp"
#include "util/flags.hpp"

void DoWork(proto::TaskMakerServer::Stub* stub, const std::string& name) {
  grpc::ClientContext context;
  remote::SetupContext(&context, name);
  std::unique_ptr<grpc::ClientReaderWriter<proto::Response, proto::Request> >
      stream(stub->GetWork(&context));
  proto::Request request;
  while (stream->Read(&request)) {
    LOG(INFO) << "[" << name << "] Got work: " << request.executable();
    std::unique_ptr<executor::Executor> executor{new executor::LocalExecutor(
        FLAGS_store_directory, FLAGS_temp_directory)};
    proto::Response response;
    try {
      response = executor->Execute(
          request, [&stub](const proto::SHA256& hash,
                           const util::File::ChunkReceiver& chunk_receiver) {
            remote::RetrieveFile(stub, hash, chunk_receiver);
          });
    } catch (std::exception& e) {
      response.set_status(proto::Status::INTERNAL_ERROR);
      response.set_error_message(e.what());
    }
    for (const proto::FileInfo& info : response.output()) {
      using std::placeholders::_1;
      using std::placeholders::_2;
      if (info.has_contents()) continue;  // Small file
      remote::SendFile(
          stub, info.hash(),
          std::bind(&executor::Executor::GetFile, executor.get(), _1, _2));
    }
    if (!stream->Write(response)) break;
    LOG(INFO) << "[" << name << "] Done";
  }
  grpc::Status status = stream->Finish();
  LOG(ERROR) << "[" << name << "] DoWork: " << status.error_message();
}

void worker(const std::string& server, const std::string& name) {
  while (true) {
    LOG(INFO) << "[" << name << "] Connecting...";
    std::shared_ptr<grpc::Channel> channel =
        grpc::CreateChannel(server, grpc::InsecureChannelCredentials());
    if (channel->GetState(/* try_to_connect = */ true) ==
        GRPC_CHANNEL_SHUTDOWN) {
      std::this_thread::sleep_for(std::chrono::seconds(1));
      LOG(ERROR) << "Connection failed";
      continue;
    }
    LOG(INFO) << "[" << name << "] Connected";
    std::unique_ptr<proto::TaskMakerServer::Stub> stub(
        proto::TaskMakerServer::NewStub(channel));
    grpc::ClientContext context;
    remote::SetupContext(&context, name);
    DoWork(stub.get(), name);
  }
}

int worker_main() {
  CHECK_NE(FLAGS_server, "") << "You need to specify a server!";

  if (FLAGS_num_cores == 0)
    FLAGS_num_cores = std::thread::hardware_concurrency();

  std::vector<std::thread> worker_threads(FLAGS_num_cores);
  for (int i = 0; i < FLAGS_num_cores; i++) {
    worker_threads[i] = std::thread(worker, FLAGS_server,
                                    FLAGS_name + "_thread" + std::to_string(i));
  }
  for (int i = 0; i < FLAGS_num_cores; i++) {
    worker_threads[i].join();
  }
  return 0;
}
