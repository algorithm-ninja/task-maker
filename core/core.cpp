#include "core/core.hpp"
#include "executor/local_executor.hpp"

namespace core {

bool Core::Run() {
  // TODO(veluca): implement this with multi-threading.
  std::unordered_map<int64_t, util::SHA256_t> known_files;
  auto get_file = [&known_files](int64_t id) {
    if (!known_files.count(id)) {
      throw std::logic_error("Unknown file requested");
    }
    return known_files.at(id);
  };

  auto set_file = [&known_files](int64_t id, const util::SHA256_t& hash) {
    // fprintf(stderr, "File %ld available\n", id);
    known_files[id] = hash;
  };

  // First, load the input files.
  for (auto& file : files_to_load_) {
    if (!callback_(TaskStatus::Start(file.get()))) return false;
    try {
      file->Load(set_file);
      if (!callback_(TaskStatus::Success(file.get()))) return false;
    } catch (const std::exception& exc) {
      if (!callback_(TaskStatus::Failure(file.get(), exc.what()))) return false;
    }
  }

  // Scan all the tasks, see if one can be executed. If so, start it.
  std::unordered_set<size_t> tasks_to_run;
  for (size_t i = 0; i < executions_.size(); i++) tasks_to_run.insert(i);
  while (true) {
    std::vector<size_t> tried_tasks;
    for (size_t task_id : tasks_to_run) {
      bool deps_ok = true;
      Execution* task = executions_[task_id].get();
      /*
      fprintf(stderr, "%s deps:", task->Description().c_str());
      for (int64_t dep : task->Deps()) fprintf(stderr, " %ld", dep);
      fprintf(stderr, "\n");
      */
      for (int64_t dep : task->Deps()) {
        if (!known_files.count(dep)) {
          deps_ok = false;
          break;
        }
      }
      if (!deps_ok) continue;
      if (!callback_(TaskStatus::Start(task))) return false;
      try {
        task->Run(get_file, set_file);
        if (!callback_(TaskStatus::Success(task))) return false;
        tried_tasks.push_back(task_id);
      } catch (executor::too_many_executions& exc) {
        if (!callback_(TaskStatus::Busy(task))) return false;
        continue;
      } catch (std::exception& exc) {
        if (!callback_(TaskStatus::Failure(task, exc.what()))) return false;
      }
    }
    for (size_t task_id : tried_tasks) tasks_to_run.erase(task_id);
    if (tried_tasks.size() == 0) break;
  }
  return true;
}

}  // namespace core
