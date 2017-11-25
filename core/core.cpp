#include "core/core.hpp"
#include "executor/local_executor.hpp"

namespace {

void PrintStatus(int total, int successful, int failed) {
  fprintf(stderr, "T: % 3d, S: % 3d, F: % 3d\n", total, successful, failed);
}

}  // namespace

namespace core {

bool Core::Run() {
  // TODO(veluca): implement this with multi-threading.
  int total_tasks = files_to_load_.size() + executions_.size();
  int successful_tasks = 0;
  int failed_tasks = 0;
  std::unordered_map<int64_t, util::SHA256_t> known_files;
  auto get_file = [&known_files](int64_t id) {
    if (!known_files.count(id)) {
      throw std::logic_error("Unknown file requested");
    }
    return known_files.at(id);
  };

  auto set_file = [&known_files](int64_t id, const util::SHA256_t& hash) {
    known_files[id] = hash;
  };

  // First, load the input files.
  for (auto& file : files_to_load_) {
    fprintf(stderr, "Loading file %s\n", file.Description().c_str());
    if (file.Load(set_file)) {
      successful_tasks++;
    } else {
      failed_tasks++;
    }
    PrintStatus(total_tasks, successful_tasks, failed_tasks);
  }

  // Scan all the tasks, see if one can be executed. If so, start it.
  std::unordered_set<size_t> tasks_to_run;
  for (size_t i = 0; i < executions_.size(); i++) tasks_to_run.insert(i);
  while (true) {
    std::vector<size_t> tried_tasks;
    for (size_t task_id : tasks_to_run) {
      bool deps_ok = true;
      Execution& task = executions_[task_id];
      for (int64_t dep : task.Deps()) {
        if (!known_files.count(dep)) {
          deps_ok = false;
          break;
        }
      }
      if (!deps_ok) continue;
      // tried_tasks.push_back(task_id);
      fprintf(stderr, "Executing %s\n", task.Description().c_str());
      try {
        if (task.Run(get_file, set_file)) {
          successful_tasks++;
        } else {
          failed_tasks++;
        }
        tried_tasks.push_back(task_id);
        PrintStatus(total_tasks, successful_tasks, failed_tasks);
      } catch (executor::too_many_executions& exc) {
        continue;
      } catch (execution_failure& exc) {
        fprintf(stderr, "Execution %s failed.\n", task.Description().c_str());
        return false;
      } catch (std::exception& exc) {
        fprintf(stderr, "Error during execution: %s\n", exc.what());
        return false;
      }
    }
    for (size_t task_id : tried_tasks) tasks_to_run.erase(task_id);
    if (tried_tasks.size() == 0) break;
  }
  return true;
}

}  // namespace core
