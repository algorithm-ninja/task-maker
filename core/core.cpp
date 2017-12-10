#include "core/core.hpp"

#include <thread>

#include "executor/local_executor.hpp"

namespace {
enum EnqueueStatus {
  QUEUE_FULL,
  CALLBACK_FALSE,
  LEFTOVERS,
  NO_TASK,
  NO_READY_TASK
};
}

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

Core::TaskStatus Core::LoadFileTask(FileID* file) {
  try {
    using namespace std::placeholders;
    file->Load(std::bind(&Core::SetFile, this, _1, _2));
    return TaskStatus::Success(file);
  } catch (const std::exception& exc) {
    return TaskStatus::Failure(file, exc.what());
  }
}

Core::TaskStatus Core::ExecuteTask(Execution* execution) {
  try {
    using namespace std::placeholders;
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
  std::vector<std::thread> threads;

  if (FLAGS_num_cores == 0) {
    FLAGS_num_cores = std::thread::hardware_concurrency();
  }
  for (int i = 0; i < FLAGS_num_cores; i++) {
    threads.emplace_back(std::bind(&Core::ThreadBody, this));
  }

  quitting_ = false;

  auto cleanup = [this, &threads]() {
    quitting_ = true;
    task_ready_.notify_all();
    for (std::thread& thread : threads) thread.join();
  };

  std::queue<std::future<TaskStatus>> waiting_tasks;
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

  auto add_tasks = [&waiting_tasks, &file_tasks, &execution_tasks, &add_task,
                    &threads, this]() {
    if (waiting_tasks.size() >= threads.size()) return QUEUE_FULL;
    while (!file_tasks.empty()) {
      FileID* file = file_tasks.front();
      file_tasks.pop();
      if (!callback_(TaskStatus::Start(file))) return CALLBACK_FALSE;
      std::packaged_task<TaskStatus()> task(
          std::bind(&Core::LoadFileTask, this, file));
      waiting_tasks.push(task.get_future());
      add_task(std::move(task));
      if (waiting_tasks.size() >= threads.size()) return QUEUE_FULL;
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
      if (!callback_(TaskStatus::Start(execution))) return CALLBACK_FALSE;
      std::packaged_task<TaskStatus()> task(
          std::bind(&Core::ExecuteTask, this, execution));
      waiting_tasks.push(task.get_future());
      add_task(std::move(task));
      if (waiting_tasks.size() >= threads.size()) return QUEUE_FULL;
    }
    if (!waiting_tasks.empty()) return NO_READY_TASK;
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

  while (should_enqueue) {
    size_t queue_size = waiting_tasks.size();
    for (size_t _ = 0; _ < queue_size; _++) {
      std::future<TaskStatus> answer_future = std::move(waiting_tasks.front());
      waiting_tasks.pop();
      if (answer_future.wait_for(std::chrono::microseconds(100)) ==
          std::future_status::ready) {
        TaskStatus answer = answer_future.get();
        if (answer.event == TaskStatus::Event::BUSY) {
          execution_tasks.push(answer.execution_info);
        }
        if (!callback_(answer)) {
          cleanup();
          return false;
        }
      } else {
        waiting_tasks.push(std::move(answer_future));
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
  cleanup();
  return true;
}

}  // namespace core
