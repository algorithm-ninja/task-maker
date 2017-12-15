#include "grpc/grpc.h"
#include "proto/server.grpc.pb.h"

namespace remote {

void SendFile(proto::TaskMakerServer::Stub* stub, grpc::ClientContext* context,
              const proto::SHA256& hash);

void RetrieveFile(proto::TaskMakerServer::Stub* stub,
                  grpc::ClientContext* context, const proto::SHA256& hash);
}  // namespace remote
