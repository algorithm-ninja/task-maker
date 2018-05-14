#include "executor/executor.hpp"
#include "grpc/grpc.h"
#include "proto/server.grpc.pb.h"
#include "util/file.hpp"

namespace remote {

void SetupContext(grpc::ClientContext* context, const std::string& name = "");

void SendFile(proto::TaskMakerServer::Stub* stub, const proto::SHA256& hash,
              const executor::Executor::RequestFileCallback& load_file);

void RetrieveFile(proto::TaskMakerServer::Stub* stub, const proto::SHA256& hash,
                  const util::File::ChunkReceiver& chunk_receiver);
}  // namespace remote
