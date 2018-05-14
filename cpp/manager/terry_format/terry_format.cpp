#include "manager/terry_format/terry_format.hpp"
#include "manager/terry_format/terry_evaluation.hpp"
#include "manager/terry_format/terry_generation.hpp"

namespace manager {
EvaluationInfo setup_request(const proto::EvaluateTerryTaskRequest& request) {
  EvaluationInfo info{};
  info.core = std::make_unique<core::Core>();
  info.core->SetStoreDirectory(request.store_dir());
  info.core->SetTempDirectory(request.temp_dir());
  info.core->SetNumCores(request.num_cores());

  info.queue = std::make_unique<manager::EventQueue>();
  info.is_remote = !request.evaluate_on().empty();

  try {
    info.generation = std::make_unique<manager::TerryGeneration>(
        info.queue.get(), info.core.get(), request.task(), request.cache_mode(),
        request.evaluate_on(), request.keep_sandbox());
    info.evaluation = std::make_unique<manager::TerryEvaluation>(
        info.queue.get(), info.core.get(),
        reinterpret_cast<manager::TerryGeneration*>(info.generation.get()),
        request.task(), request.exclusive(), request.cache_mode(),
        request.evaluate_on(), request.keep_sandbox());

    for (const proto::TerrySolution& solution : request.solutions()) {
      const proto::SourceFile& source = solution.solution();
      int64_t seed = solution.seed();
      info.source_files[source.path()] = manager::SourceFile::FromProto(
          info.queue.get(), info.core.get(), source, false,
          request.keep_sandbox(), request.cache_mode(), request.evaluate_on());
      auto* evaluation =
          reinterpret_cast<manager::TerryEvaluation*>(info.evaluation.get());
      evaluation->Evaluate(info.source_files[source.path()].get(), seed);
    }
  } catch (std::exception& ex) {
    LOG(ERROR) << "Failed to prepare core: " << ex.what();
    info.queue->FatalError(std::string("Failed to start the core! ") +
                           ex.what());
    info.queue->Stop();
  }

  return info;
}

void run_core(const proto::EvaluateTerryTaskRequest& request,
              int64_t current_id, std::map<int64_t, EvaluationInfo>* running) {
  (*running)[current_id].running_thread = std::thread([request, current_id,
                                                       running] {
    EvaluationInfo& info = (*running)[current_id];
    LOG(INFO) << "Starting new core for terry request " << current_id;
    try {
      if (info.core->Run()) {
        LOG(INFO) << "The core for request " << current_id << " has succeeded";
        info.queue->Stop();
        if (request.dry_run()) {
          LOG(INFO) << "Dry-run mode, compiled files not saved";
          return;
        }
      } else {
        info.queue->FatalError("The core failed");
        LOG(WARNING) << "The core for request " << current_id << " has failed";
        info.queue->Stop();
      }
    } catch (const std::exception& ex) {
      LOG(WARNING) << "The core for request " << current_id
                   << " has failed with exception: " << ex.what();
      info.queue->FatalError(std::string("The core failed! ") + ex.what());
      info.queue->Stop();
    }
  });
}
}  // namespace manager
