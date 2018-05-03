#ifndef EXECUTOR_LOCAL_EXECUTOR_HPP
#define EXECUTOR_LOCAL_EXECUTOR_HPP

#include <mutex>

#include "executor/executor.hpp"
#include "sandbox/sandbox.hpp"

namespace executor {

class too_many_executions : public std::runtime_error {
 public:
  explicit too_many_executions(const char* msg) : std::runtime_error(msg) {}
};

class LocalExecutor : public Executor {
 public:
  std::string Id() const override { return "LOCAL"; }
  proto::Response Execute(const proto::Request& request,
                          const RequestFileCallback& file_callback) override;
  void GetFile(const proto::SHA256& hash,
               const util::File::ChunkReceiver& chunk_receiver) override;

  LocalExecutor(const LocalExecutor&) = delete;
  LocalExecutor& operator=(const LocalExecutor&) = delete;
  LocalExecutor(LocalExecutor&&) = delete;
  LocalExecutor& operator=(LocalExecutor&&) = delete;
  ~LocalExecutor() override = default;
  LocalExecutor(std::string store_directory, std::string temp_directory,
                size_t num_cores = 0);

 private:
  class ThreadGuard {
   public:
    explicit ThreadGuard(bool exclusive = false);
    ~ThreadGuard();
    ThreadGuard(const ThreadGuard&) = delete;
    ThreadGuard& operator=(const ThreadGuard&) = delete;
    ThreadGuard(ThreadGuard&&) = delete;
    ThreadGuard& operator=(ThreadGuard&&) = delete;

    static void SetMaxThreads(size_t num);

   private:
    static size_t& MaxThreads();
    static size_t& CurThreads();
    static std::mutex& Mutex();
    bool exclusive_;
  };

  static const constexpr char* kBoxDir = "box";

  void MaybeRequestFile(const proto::FileInfo& info,
                        const RequestFileCallback& file_callback);

  void PrepareFile(const proto::FileInfo& info, const std::string& tmpdir,
                   sandbox::ExecutionOptions* options,
                   std::vector<std::string>* input_files);

  void RetrieveFile(const proto::FileInfo& info, const std::string& tmpdir,
                    proto::Response* options);

  std::string store_directory_;
  std::string temp_directory_;
};

}  // namespace executor

#endif
