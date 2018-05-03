#include "executor/executor.hpp"
#include "grpc++/channel.h"
#include "proto/server.grpc.pb.h"

namespace executor {

class RemoteExecutor : public Executor {
 public:
  // A string that identifies this executor.
  std::string Id() const override { return remote_address_; }

  proto::Response Execute(const proto::Request& request,
                          const RequestFileCallback& file_callback) override;
  void GetFile(const proto::SHA256& hash,
               const util::File::ChunkReceiver& chunk_receiver) override;

  explicit RemoteExecutor(std::string address)
      : remote_address_(std::move(address)) {}
  ~RemoteExecutor() override = default;
  RemoteExecutor(const RemoteExecutor&) = delete;
  RemoteExecutor& operator=(const RemoteExecutor&) = delete;
  RemoteExecutor(RemoteExecutor&&) = delete;
  RemoteExecutor& operator=(RemoteExecutor&&) = delete;

 public:
  void MaybeGetNewChannelAndStub();
  std::string remote_address_;
  std::shared_ptr<grpc::Channel> channel_;
  std::unique_ptr<proto::TaskMakerServer::Stub> stub_;
};

}  // namespace executor
