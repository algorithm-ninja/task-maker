#include "core/core.hpp"
#include "executor/local_executor.hpp"

namespace core {

bool Core::Run() {
  std::vector<std::thread> threads;

  auto tear_down = [this, &threads] {
    if (cacher_) cacher_->TearDown();
    quitting_ = true;
    task_ready_.notify_all();
    for (auto& thread : threads) thread.join();
  };

  if (cacher_) cacher_->Setup();

  BuildDependencyGraph();
  if (!LoadInitialFiles()) {
    tear_down();
    return false;
  }

  threads.reserve(num_cores_);
  for (size_t i = 0; i < num_cores_; i++)
    threads.emplace_back([this] { ThreadBody(); });

  while (!quitting_) {
    std::unique_lock<std::mutex> lck(job_mutex_);
    if (waiting_jobs_.empty() && ready_tasks_.empty() &&
        running_jobs_.empty() && completed_jobs_.empty())
      break;
    while (completed_jobs_.empty() && !quitting_) {
      task_complete_.wait(lck);
    }
    if (quitting_) break;
    RunningTask task = std::move(completed_jobs_.front());
    completed_jobs_.pop_front();
    if (!ProcessTaskCompleted(&task)) {
      lck.unlock();
      tear_down();
      return false;
    }
  }
  tear_down();
  for (const auto& file : files_to_load_)
    file->callback_(TaskStatus::Finish(file.get(), !failed_));
  for (const auto& exec : executions_)
    exec->callback_(TaskStatus::Finish(exec.get(), !failed_));
  return !failed_;
}

void Core::ThreadBody() {
  while (!quitting_) {
    std::unique_lock<std::mutex> lck(job_mutex_);
    while (!quitting_ && ready_tasks_.empty()) task_ready_.wait(lck);
    if (quitting_) break;

    ReadyTask task = std::move(ready_tasks_.front());
    ready_tasks_.pop();
    if (!task.job->execution->callback_(
            TaskStatus::Start(task.job->execution))) {
      LOGE << "Failed to start job: " << task.job->execution->Description();
      quitting_ = true;
      failed_ = true;
      task_ready_.notify_all();
      return;
    }
    RunningTask running_task{RunningTaskInfo(task.job->execution), task.job,
                             task.task.get_future()};
    size_t id = task_id_++;
    running_jobs_.emplace(id, std::move(running_task));
    lck.unlock();
    task.task();
    lck.lock();
    completed_jobs_.push_back(std::move(running_jobs_.at(id)));
    running_jobs_.erase(id);
    task_complete_.notify_all();
  }
}

TaskStatus Core::ExecuteTask(Execution* execution) {
  try {
    execution->Run(
        [this](int64_t id) { return GetFile(id); },
        [this](int64_t id, const util::SHA256_t& hash) { SetFile(id, hash); });
    return TaskStatus::Success(execution);
  } catch (std::exception& exc) {
    std::string tmp = exc.what();
    std::string needle = "worker busy";
    size_t start = tmp.length() - needle.length();
    bool endswith = true;
    for (size_t i = 0; i < needle.length(); i++) {
      if (needle[i] != tmp[start + i]) {
        endswith = false;
        break;
      }
    }
    if (endswith) return TaskStatus::Busy(execution);
    return TaskStatus::Failure(execution, exc.what());
  }
}

void Core::BuildDependencyGraph() {
  for (const auto& job : jobs_) {
    auto deps = job->execution->Deps();
    for (int64_t dep : deps) dependents_[dep].push_back(job.get());
    job->pending_deps = deps.size();
    if (deps.empty())
      EnqueueJob(job.get());
    else
      waiting_jobs_.insert(job.get());
  }
  IF_LOG(plog::verbose) {
    for (const auto& job : jobs_) {
      LOGV << job->execution->Description();
      for (auto id : job->execution->Produces()) {
        for (auto next : dependents_[id])
          LOGV << "  - [" << id << "] " << next->execution->Description();
      }
    }
  }
}

void Core::EnqueueJob(Job* job) {
  std::packaged_task<TaskStatus()> task(
      [this, job] { return ExecuteTask(job->execution); });
  ready_tasks_.push(ReadyTask{job, std::move(task)});
  task_ready_.notify_all();
}

void Core::MarkAsSuccessful(Job* job) {
  for (int64_t file_id : job->execution->Produces()) MarkAsSuccessful(file_id);
}

void Core::MarkAsSuccessful(int64_t file_id) {
  for (Job* next : dependents_[file_id]) {
    next->pending_deps--;
    if (next->pending_deps == 0) {
      EnqueueJob(next);
      waiting_jobs_.erase(next);
    }
  }
}

void Core::MarkAsFailed(Job* job) {
  for (int64_t file_id : job->execution->Produces()) MarkAsFailed(file_id);
}

void Core::MarkAsFailed(int64_t file_id) {
  for (Job* next : dependents_[file_id]) {
    // the job has already thrown away
    if (waiting_jobs_.count(next) == 0) continue;
    waiting_jobs_.erase(next);
    MarkAsFailed(next);
  }
}

bool Core::LoadInitialFiles() {
  for (const auto& file : files_to_load_) {
    if (!file->callback_(TaskStatus::Start(file.get()))) {
      LOGE << "Failed to start loading: " << file->Description();
      return false;
    }
    try {
      file->Load([this](int64_t id, const util::SHA256_t& hash) {
        SetFile(id, hash);
      });
      if (!file->callback_(TaskStatus::Success(file.get()))) {
        LOGE << "Failed to complete loading: " << file->Description();
        return false;
      }
      MarkAsSuccessful(file->ID());
    } catch (const std::exception& exc) {
      if (!file->callback_(TaskStatus::Failure(file.get(), exc.what()))) {
        LOGE << "Failed loading: " << file->Description();
        return false;
      }
      MarkAsFailed(file->ID());
    }
  }
  return true;
}

bool Core::ProcessTaskCompleted(RunningTask* task) {
  LOGV << "Task completed: " << task->info.description;
  TaskStatus answer = task->future.get();
  Job* job = task->job;
  switch (answer.event) {
    case TaskStatus::BUSY:
      EnqueueJob(job);
      break;
    case TaskStatus::SUCCESS:
      if (answer.execution_info->Success())
        MarkAsSuccessful(job);
      else
        MarkAsFailed(job);
      if (!job->execution->callback_(answer)) {
        LOGE << "Task success callback failed: "
             << job->execution->Description();
        return false;
      }
      break;
    case TaskStatus::FAILURE:
      MarkAsFailed(job);
      if (!job->execution->callback_(answer)) {
        LOGE << "Task failed: " << job->execution->Description() << "\n"
             << job->execution->response_.DebugString();
        return false;
      }
      break;
    default:
      LOGF << "Invalid event type: " << answer.type;
      return false;
  }
  return true;
}

std::vector<RunningTaskInfo> Core::RunningTasks() const {
  std::lock_guard<std::mutex> lck(job_mutex_);
  std::vector<RunningTaskInfo> tasks;
  for (const auto& task : running_jobs_) tasks.emplace_back(task.second.info);
  return tasks;
}

}  // namespace core
