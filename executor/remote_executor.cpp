#include "executor/remote_executor.hpp"
#include "gflags/gflags.h"
#include "grpc++/client_context.h"
#include "grpc++/create_channel.h"
#include "grpc++/security/credentials.h"
#include "grpc/grpc.h"
#include "remote/common.hpp"

namespace executor {

proto::Response RemoteExecutor::Execute(
    const proto::Request& request, const RequestFileCallback& file_callback) {
  MaybeGetNewChannelAndStub();
  for (const proto::FileInfo& info : request.input()) {
    if (info.has_contents()) continue;  // Small file
    remote::SendFile(stub_.get(), info.hash(), file_callback);
  }
  grpc::ClientContext context;
  remote::SetupContext(&context);
  proto::Response response;
  grpc::Status status = stub_->Execute(&context, request, &response);
  if (status.ok()) return response;
  throw std::runtime_error(status.error_message());
}

void RemoteExecutor::GetFile(const proto::SHA256& hash,
                             const util::File::ChunkReceiver& chunk_receiver) {
  MaybeGetNewChannelAndStub();
  remote::RetrieveFile(stub_.get(), hash, chunk_receiver);
}

void RemoteExecutor::MaybeGetNewChannelAndStub() {
  if (channel_ &&
      channel_->GetState(/* try_to_connect = */ true) != GRPC_CHANNEL_SHUTDOWN)
    return;
  channel_ =
      grpc::CreateChannel(remote_address_, grpc::InsecureChannelCredentials());
  stub_ = proto::TaskMakerServer::NewStub(channel_);
}

}  // namespace executor
