#include <functional>
#include <memory>
#include <thread>
#include <vector>

#include "executor/local_executor.hpp"
#include "gflags/gflags.h"
#include "grpc++/channel.h"
#include "grpc++/client_context.h"
#include "grpc++/create_channel.h"
#include "grpc++/security/credentials.h"
#include "grpc/grpc.h"
#include "proto/server.grpc.pb.h"
#include "remote/common.hpp"
#include "util/flags.hpp"

DEFINE_string(server, "", "server to connect to");
DEFINE_string(name, "unnamed_worker", "name that identifies this worker");

void DoWork(proto::TaskMakerServer::Stub* stub, const std::string& name) {
  grpc::ClientContext context;
  remote::SetupContext(&context, name);
  std::unique_ptr<grpc::ClientReaderWriter<proto::Response, proto::Request> >
      stream(stub->GetWork(&context));
  proto::Request request;
  while (stream->Read(&request)) {
    std::cerr << "Got work: " << request.executable() << std::endl;
    std::unique_ptr<executor::Executor> executor{new executor::LocalExecutor()};
    using namespace std::placeholders;
    proto::Response response;
    try {
      response = executor->Execute(
          request, [&stub](const proto::SHA256& hash,
                           const util::File::ChunkReceiver& chunk_receiver) {
            std::cerr << "Retrieving file " << hash.DebugString() << std::endl;
            remote::RetrieveFile(stub, hash, chunk_receiver);
            std::cerr << "Got file " << hash.DebugString() << std::endl;
          });
    } catch (std::exception& e) {
      response.set_status_code(proto::Status::INTERNAL_ERROR);
      response.set_error_message(e.what());
    }
    for (const proto::FileInfo& info : response.output()) {
      if (info.has_contents()) continue;  // Small file
      std::cerr << "Sending file " << info.hash().DebugString() << std::endl;
      remote::SendFile(
          stub, info.hash(),
          std::bind(&executor::Executor::GetFile, executor.get(), _1, _2));
      std::cerr << "Sent file " << info.hash().DebugString() << std::endl;
    }
    std::cerr << "Done, sending answer..." << std::endl;
    if (!stream->Write(response)) break;
    std::cerr << "Ok" << std::endl;
  }
  grpc::Status status = stream->Finish();
  std::cerr << "DoWork: " << status.error_message() << std::endl;
}

void worker(const std::string& server, const std::string& name) {
  while (true) {
    std::cerr << "Worker connecting..." << std::endl;
    std::shared_ptr<grpc::Channel> channel =
        grpc::CreateChannel(server, grpc::InsecureChannelCredentials());
    if (channel->GetState(/* try_to_connect = */ true) ==
        GRPC_CHANNEL_SHUTDOWN) {
      std::this_thread::sleep_for(std::chrono::seconds(1));
      std::cerr << "Connection failed" << std::endl;
      continue;
    }
    std::unique_ptr<proto::TaskMakerServer::Stub> stub(
        proto::TaskMakerServer::NewStub(channel));
    grpc::ClientContext context;
    remote::SetupContext(&context, name);
    DoWork(stub.get(), name);
  }
}

int main(int argc, char** argv) {
  gflags::ParseCommandLineFlags(&argc, &argv, true);
  if (FLAGS_server == "") {
    std::cerr << "You need to specify a server!" << std::endl;
    return 1;
  }
  std::vector<std::thread> worker_threads;
  if (FLAGS_num_cores == 0) {
    FLAGS_num_cores = std::thread::hardware_concurrency();
  }
  for (int i = 0; i < FLAGS_num_cores; i++) {
    worker_threads.emplace_back(worker, FLAGS_server,
                                FLAGS_name + "_thread" + std::to_string(i));
  }
  for (int i = 0; i < FLAGS_num_cores; i++) {
    worker_threads[i].join();
  }
}
