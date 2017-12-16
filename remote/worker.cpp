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
#include "remote/common.hpp"
#include "util/flags.hpp"

DEFINE_string(server, "", "server to connect to");

void DoWork(proto::TaskMakerServer::Stub* stub) {
  grpc::ClientContext context;
  remote::SetupContext(&context);
  std::unique_ptr<grpc::ClientReaderWriter<proto::Response, proto::Request> >
      stream(stub->GetWork(&context));
  proto::Request request;
  while (stream->Read(&request)) {
    std::unique_ptr<executor::Executor> executor{new executor::LocalExecutor()};
    using namespace std::placeholders;
    proto::Response response = executor->Execute(
        request, std::bind(remote::RetrieveFile, stub, _1, _2));
    for (const proto::FileInfo& info : response.output()) {
      if (info.has_contents()) continue;  // Small file
      remote::SendFile(
          stub, info.hash(),
          std::bind(&executor::Executor::GetFile, executor.get(), _1, _2));
    }
    if (!stream->Write(response)) break;
  }
  grpc::Status status = stream->Finish();
  std::cerr << "DoWork: " << status.error_message() << std::endl;
}

void worker(const std::string& server) {
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
    DoWork(stub.get());
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
    worker_threads.emplace_back(worker, FLAGS_server);
  }
  for (int i = 0; i < FLAGS_num_cores; i++) {
    worker_threads[i].join();
  }
}
