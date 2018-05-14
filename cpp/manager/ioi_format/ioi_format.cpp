#include "manager/ioi_format/ioi_format.hpp"
#include "manager/ioi_format/ioi_evaluation.hpp"
#include "manager/ioi_format/ioi_generation.hpp"

namespace manager {
EvaluationInfo setup_request(const proto::EvaluateTaskRequest& request) {
  EvaluationInfo info{};
  info.core = std::make_unique<core::Core>();
  info.core->SetStoreDirectory(request.store_dir());
  info.core->SetTempDirectory(request.temp_dir());
  info.core->SetNumCores(request.num_cores());

  info.queue = std::make_unique<manager::EventQueue>();
  info.is_remote = !request.evaluate_on().empty();

  try {
    info.generation = std::make_unique<manager::IOIGeneration>(
        info.queue.get(), info.core.get(), request.task(), request.cache_mode(),
        request.evaluate_on(), request.keep_sandbox());

    info.evaluation = std::make_unique<manager::IOIEvaluation>(
        info.queue.get(), info.core.get(),
        reinterpret_cast<manager::IOIGeneration*>(info.generation.get()),
        request.task(), request.exclusive(), request.cache_mode(),
        request.evaluate_on(), request.keep_sandbox());

    std::map<proto::Language, proto::GraderInfo> graders;
    for (const proto::GraderInfo& grader : request.task().grader_info())
      graders[grader.for_language()] = grader;

    for (const proto::SourceFile& source : request.solutions()) {
      if (graders.count(source.language()) == 1) {
        info.source_files[source.path()] = manager::SourceFile::FromProto(
            info.queue.get(), info.core.get(), source, false,
            request.keep_sandbox(), request.cache_mode(), request.evaluate_on(),
            &graders[source.language()]);
      } else {
        info.source_files[source.path()] = manager::SourceFile::FromProto(
            info.queue.get(), info.core.get(), source, false,
            request.keep_sandbox(), request.cache_mode(),
            request.evaluate_on());
      }
      auto* evaluation =
          reinterpret_cast<manager::IOIEvaluation*>(info.evaluation.get());
      evaluation->Evaluate(info.source_files[source.path()].get());
    }
  } catch (std::exception& ex) {
    LOG(ERROR) << "Failed to prepare core: " << ex.what();
    info.queue->FatalError(std::string("Failed to start the core! ") +
                           ex.what());
    info.queue->Stop();
  }

  return info;
}

void run_core(const proto::EvaluateTaskRequest& request, int64_t current_id,
              std::map<int64_t, EvaluationInfo>* running) {
  (*running)[current_id].running_thread = std::thread([request, current_id,
                                                       running] {
    EvaluationInfo& info = (*running)[current_id];
    LOG(INFO) << "Starting new core for request " << current_id;
    try {
      if (info.core->Run()) {
        LOG(INFO) << "The core for request " << current_id << " has succeeded";
        info.queue->Stop();
        if (request.dry_run()) {
          LOG(INFO) << "Dry-run mode, inputs/outputs/checker not saved";
          return;
        }
        auto* generation =
            reinterpret_cast<manager::IOIGeneration*>(info.generation.get());
        if (request.task().has_checker() && !request.write_checker_to().empty())
          generation->WriteChecker(request);
        generation->WriteInputs(request);
        generation->WriteOutputs(request);
      } else {
        info.queue->FatalError("The core failed!");
        LOG(WARNING) << "The core for request " << current_id << " has failed";
        info.queue->Stop();
      }
    } catch (const std::exception& ex) {
      LOG(WARNING) << "The core for request " << current_id
                   << " has failed with an excetpion: " << ex.what();
      info.queue->FatalError(std::string("The core failed! ") + ex.what());
      info.queue->Stop();
    }
  });
}
}  // namespace manager
