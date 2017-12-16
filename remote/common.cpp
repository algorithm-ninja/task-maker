#include "remote/common.hpp"

namespace remote {

void SetupContext(grpc::ClientContext* context) {}

void SendFile(proto::TaskMakerServer::Stub* stub, const proto::SHA256& hash,
              const executor::Executor::RequestFileCallback& load_file) {
  grpc::ClientContext context;
  SetupContext(&context);
  proto::SendFileResponse response;
  std::unique_ptr<grpc::ClientWriter<proto::FileContents>> writer(
      stub->SendFile(&context, &response));
  proto::FileContents hdr;
  *hdr.mutable_hash() = hash;
  if (writer->Write(hdr)) {
    load_file(hash, [&writer](const proto::FileContents& contents) {
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

void RetrieveFile(proto::TaskMakerServer::Stub* stub, const proto::SHA256& hash,
                  const util::File::ChunkReceiver& chunk_receiver) {
  grpc::ClientContext context;
  SetupContext(&context);
  std::unique_ptr<grpc::ClientReader<proto::FileContents>> reader(
      stub->RetrieveFile(&context, hash));
  proto::FileContents contents;
  while (reader->Read(&contents)) {
    chunk_receiver(contents);
  }
  grpc::Status status = reader->Finish();
  if (!status.ok() && status.error_code()) {
    throw std::runtime_error(status.error_message());
  }
}
}  // namespace remote
