#include "remote/common.hpp"
#include "util/file.hpp"

namespace remote {

void SendFile(proto::TaskMakerServer::Stub* stub, grpc::ClientContext* context,
              const proto::SHA256& hash) {
  proto::SendFileResponse response;
  std::unique_ptr<grpc::ClientWriter<proto::FileContents>> writer(
      stub->SendFile(context, &response));
  proto::FileContents hdr;
  *hdr.mutable_hash() = hash;
  if (writer->Write(hdr)) {
    util::File::Read(util::File::ProtoSHAToPath(hash),
                     [&writer](const proto::FileContents& contents) {
                       writer->Write(contents);
                     });
    hdr.set_last(true);
    writer->Write(hdr);
  }
  grpc::Status status = writer->Finish();
  if (!status.ok() && status.error_code() != grpc::StatusCode::ALREADY_EXISTS) {
    throw std::runtime_error(status.error_message());
  }
}

void RetrieveFile(proto::TaskMakerServer::Stub* stub,
                  grpc::ClientContext* context, const proto::SHA256& hash) {
  std::unique_ptr<grpc::ClientReader<proto::FileContents>> reader(
      stub->RetrieveFile(context, hash));
  util::File::Write(util::File::ProtoSHAToPath(hash),
                    [&reader](const util::File::ChunkReceiver& chunk_receiver) {
                      proto::FileContents contents;
                      while (reader->Read(&contents)) {
                        chunk_receiver(contents);
                      }
                      grpc::Status status = reader->Finish();
                      if (!status.ok() && status.error_code()) {
                        throw std::runtime_error(status.error_message());
                      }
                    });
}
}  // namespace remote
