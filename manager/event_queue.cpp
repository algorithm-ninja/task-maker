#include "manager/event_queue.hpp"

namespace manager {

void EventQueue::Enqueue(proto::Event&& event) {
  absl::MutexLock lck(&queue_mutex_);
  queue_.push(event);
}

absl::optional<proto::Event> EventQueue::Dequeue() {
  absl::MutexLock lck(&queue_mutex_);
  auto cond = [this]() {
    queue_mutex_.AssertHeld();
    return stopped_ || !queue_.empty();
  };
  queue_mutex_.Await(absl::Condition(&cond));
  if (queue_.empty()) return {};
  absl::optional<proto::Event> event = std::move(queue_.front());
  queue_.pop();
  return event;
}

void EventQueue::Stop() {
  absl::MutexLock lck(&queue_mutex_);
  stopped_ = true;
}
}  // namespace manager
