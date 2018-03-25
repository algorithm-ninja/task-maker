#include "core/core.hpp"
#include "executor/local_executor.hpp"
#include "glog/logging.h"

namespace {
enum EnqueueStatus {
  QUEUE_FULL,
  CALLBACK_FALSE,
  LEFTOVERS,
  NO_TASK,
  NO_READY_TASK
};
}  // namespace

namespace core {

void Core::ThreadBody() {
  while (!quitting_) {
    std::unique_lock<std::mutex> lck(task_mutex_);
    while (!quitting_ && tasks_.empty()) {
      task_ready_.wait(lck);
    }
    if (quitting_) break;
    std::packaged_task<TaskStatus()> task = std::move(tasks_.front());
    tasks_.pop();
    lck.unlock();
    task();
  }
}

TaskStatus Core::LoadFileTask(FileID* file) {
  try {
    using std::placeholders::_1;
    using std::placeholders::_2;
    file->Load(std::bind(&Core::SetFile, this, _1, _2));
    return TaskStatus::Success(file);
  } catch (const std::exception& exc) {
    return TaskStatus::Failure(file, exc.what());
  }
}

TaskStatus Core::ExecuteTask(Execution* execution) {
  LOG(INFO) << execution->Description();
  try {
    using std::placeholders::_1;
    using std::placeholders::_2;
    execution->Run(std::bind(&Core::GetFile, this, _1),
                   std::bind(&Core::SetFile, this, _1, _2));
    return TaskStatus::Success(execution);
  } catch (executor::too_many_executions& exc) {
    return TaskStatus::Busy(execution);
  } catch (std::exception& exc) {
    return TaskStatus::Failure(execution, exc.what());
  }
}

bool Core::Run() {
  // TODO(veluca): detect dependency cycles.
  // TODO(veluca): think about how to automatically resize the thread pool.

  // Load up cache.
  cacher_->Setup();

  std::vector<std::thread> threads(num_cores_);
  for (int i = 0; i < num_cores_; i++)
    threads[i] = std::thread(std::bind(&Core::ThreadBody, this));

  quitting_ = false;

  auto cleanup = [this, &threads]() {
    cacher_->TearDown();
    quitting_ = true;
    task_ready_.notify_all();
    for (std::thread& thread : threads) thread.join();
  };

  try {
    std::queue<FileID*> file_tasks;
    for (const auto& file : files_to_load_) file_tasks.push(file.get());
    std::queue<Execution*> execution_tasks;
    for (const auto& execution : executions_)
      execution_tasks.push(execution.get());

    auto add_task = [this](std::packaged_task<TaskStatus()> task) {
      std::lock_guard<std::mutex> lck(task_mutex_);
      tasks_.push(std::move(task));
      task_ready_.notify_all();
    };

    auto add_tasks = [&file_tasks, &execution_tasks, &add_task, &threads,
                      this]() {
      if (running_tasks_.size() >= threads.size()) return QUEUE_FULL;
      while (!file_tasks.empty()) {
        FileID* file = file_tasks.front();
        file_tasks.pop();
        if (!file->callback_(TaskStatus::Start(file))) {
          LOG(ERROR) << "Task start failed: " << file->Description()
                     << " [FILE_LOAD]";
          return CALLBACK_FALSE;
        }
        std::packaged_task<TaskStatus()> task(
            std::bind(&Core::LoadFileTask, this, file));
        {
          std::lock_guard<std::mutex> lck(running_tasks_lock_);
          running_tasks_.emplace(file, task.get_future());
        }
        add_task(std::move(task));
        if (running_tasks_.size() >= threads.size()) return QUEUE_FULL;
      }
      size_t reenqueued_tasks = 0;
      while (reenqueued_tasks < execution_tasks.size() &&
             !execution_tasks.empty()) {
        Execution* execution = execution_tasks.front();
        execution_tasks.pop();
        bool ready = true;
        for (int64_t dep : execution->Deps()) {
          if (!FilePresent(dep)) ready = false;
        }
        if (!ready) {
          execution_tasks.push(execution);
          reenqueued_tasks++;
          continue;
        }
        if (!execution->callback_(TaskStatus::Start(execution))) {
          LOG(ERROR) << "Task start failed: " << execution->Description()
                     << " [EXECUTION]";
          return CALLBACK_FALSE;
        }
        std::packaged_task<TaskStatus()> task(
            std::bind(&Core::ExecuteTask, this, execution));
        {
          std::lock_guard<std::mutex> lck(running_tasks_lock_);
          running_tasks_.emplace(execution, task.get_future());
        }
        add_task(std::move(task));
        if (running_tasks_.size() >= threads.size()) return QUEUE_FULL;
      }
      if (!running_tasks_.empty()) return NO_READY_TASK;
      return execution_tasks.empty() ? NO_TASK : LEFTOVERS;
    };

    bool should_enqueue = true;

    switch (add_tasks()) {
      case CALLBACK_FALSE:
        cleanup();
        return false;
      case NO_TASK:
      case LEFTOVERS:
        should_enqueue = false;
        break;
      case NO_READY_TASK:
      case QUEUE_FULL:
        break;
    }

    while ((should_enqueue or !running_tasks_.empty()) && !quitting_) {
      {
        std::lock_guard<std::mutex> lck(running_tasks_lock_);
        size_t queue_size = running_tasks_.size();
        for (size_t _ = 0; _ < queue_size; _++) {
          RunningTask running_task = std::move(running_tasks_.front());
          running_tasks_.pop();
          if (running_task.future.wait_for(std::chrono::microseconds(100)) ==
              std::future_status::ready) {
            if (running_task.info.type == core::RunningTaskInfo::FILE_LOAD)
              VLOG(1) << "File loaded: " << running_task.info.description;
            else
              VLOG(1) << "Execution completed: "
                      << running_task.info.description;
            TaskStatus answer = running_task.future.get();
            if (answer.event == TaskStatus::Event::BUSY) {
              execution_tasks.push(answer.execution_info);
            }
            std::function<bool(const TaskStatus&)> callback =
                answer.type == TaskStatus::Type::EXECUTION
                    ? answer.execution_info->callback_
                    : answer.file_info->callback_;
            if (!callback(answer)) {
              cleanup();
              if (running_task.info.type == core::RunningTaskInfo::FILE_LOAD)
                LOG(ERROR) << "Task execution failed "
                           << running_task.info.description << " [FILE_LOAD]";
              else
                LOG(ERROR) << "Task execution failed "
                           << running_task.info.description << " [EXECUTION]";
              return false;
            }
          } else {
            running_tasks_.push(std::move(running_task));
          }
        }
      }
      switch (add_tasks()) {
        case CALLBACK_FALSE:
          cleanup();
          return false;
        case NO_TASK:
        case LEFTOVERS:
          should_enqueue = false;
          break;
        case NO_READY_TASK:
        case QUEUE_FULL:
          break;
      }
    }
    if (!running_tasks_.empty()) {
      std::lock_guard<std::mutex> lck(running_tasks_lock_);
      size_t queue_len = running_tasks_.size();
      LOG(WARNING) << "There are " << queue_len << " running tasks";
      for (size_t i = 0; i < queue_len; i++) {
        LOG(WARNING) << "   " << running_tasks_.front().info.description;
        running_tasks_.push(std::move(running_tasks_.front()));
        running_tasks_.pop();
      }
    }
    CHECK(running_tasks_.empty() or quitting_);
  } catch (std::exception& e) {
    cleanup();
    throw std::runtime_error(e.what());
  }
  cleanup();
  return true;
}

std::vector<RunningTaskInfo> Core::RunningTasks() const {
  std::lock_guard<std::mutex> lck(running_tasks_lock_);
  std::vector<RunningTaskInfo> tasks;
  size_t queue_size = running_tasks_.size();
  for (size_t _ = 0; _ < queue_size; _++) {
    RunningTask task = std::move(running_tasks_.front());
    running_tasks_.pop();
    tasks.push_back(task.info);
    running_tasks_.push(std::move(task));
  }
  return tasks;
}

}  // namespace core
