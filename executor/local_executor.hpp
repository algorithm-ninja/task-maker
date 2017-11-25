#ifndef EXECUTOR_LOCAL_EXECUTOR_HPP
#define EXECUTOR_LOCAL_EXECUTOR_HPP
#include "executor/executor.hpp"

#include <mutex>

#include "gflags/gflags.h"
#include "sandbox/sandbox.hpp"

DECLARE_int32(num_cores);
DECLARE_string(temp_directory);
DECLARE_string(store_directory);

namespace executor {

class too_many_executions : public std::runtime_error {
 public:
  explicit too_many_executions(const char* msg) : std::runtime_error(msg) {}
};

class LocalExecutor : public Executor {
 public:
  proto::Response Execute(const proto::Request& request,
                          const RequestFileCallback& file_callback) override;
  void GetFile(const proto::SHA256& hash,
               const util::File::ChunkReceiver& chunk_receiver) override;

  LocalExecutor(const LocalExecutor&) = delete;
  LocalExecutor& operator=(const LocalExecutor&) = delete;
  LocalExecutor(LocalExecutor&&) = delete;
  LocalExecutor& operator=(LocalExecutor&&) = delete;
  ~LocalExecutor() override = default;
  LocalExecutor();

 private:
  class ThreadGuard {
   public:
    explicit ThreadGuard(bool exclusive = false);
    ~ThreadGuard();
    ThreadGuard(const ThreadGuard&) = delete;
    ThreadGuard& operator=(const ThreadGuard&) = delete;
    ThreadGuard(ThreadGuard&&) = delete;
    ThreadGuard& operator=(ThreadGuard&&) = delete;

   private:
    static int32_t& MaxThreads();
    static int32_t& CurThreads();
    static std::mutex& Mutex();
    bool exclusive_;
  };

  static const constexpr char* kBoxDir = "box";

  std::string ProtoSHAToPath(const proto::SHA256& hash);

  void MaybeRequestFile(const proto::FileInfo& info,
                        const RequestFileCallback& file_callback);

  void PrepareFile(const proto::FileInfo& info, const std::string& tmpdir,
                   sandbox::ExecutionOptions* options);

  void RetrieveFile(const proto::FileInfo& info, const std::string& tmpdir,
                    proto::Response* options);
};

}  // namespace executor

#endif
