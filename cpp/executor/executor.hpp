#ifndef EXECUTOR_EXECUTOR_HPP
#define EXECUTOR_EXECUTOR_HPP
#include <functional>
#include <vector>

#include "proto/request.pb.h"
#include "proto/response.pb.h"
#include "proto/sha256.pb.h"
#include "util/file.hpp"

namespace executor {

class Executor {
 public:
  using RequestFileCallback =
      std::function<void(const proto::SHA256& hash,
                         const util::File::ChunkReceiver& chunk_receiver)>;

  // A string that identifies this executor.
  virtual std::string Id() const = 0;

  // Executes a request and returns the response, after possibly using the
  // provided file_callback to load missing files.
  virtual proto::Response Execute(const proto::Request& request,
                                  const RequestFileCallback& file_callback) = 0;
  virtual void GetFile(const proto::SHA256& hash,
                       const util::File::ChunkReceiver& chunk_receiver) = 0;

  Executor() = default;
  virtual ~Executor() = default;
  Executor(const Executor&) = delete;
  Executor& operator=(const Executor&) = delete;
  Executor(Executor&&) = delete;
  Executor& operator=(Executor&&) = delete;
};

}  // namespace executor

#endif
