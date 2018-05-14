#include "manager/event_queue.hpp"

namespace manager {

void EventQueue::Enqueue(proto::Event&& event) {
  std::unique_lock<std::mutex> lck(queue_mutex_);
  queue_.push(event);
  queue_cv_.notify_all();
}

bool EventQueue::Dequeue(proto::Event* out) {
  std::unique_lock<std::mutex> lck(queue_mutex_);
  while (!stopped_ && queue_.empty()) {
    queue_cv_.wait(lck);
  }
  if (queue_.empty()) return false;
  out->Swap(&queue_.front());
  queue_.pop();
  return true;
}

void EventQueue::Stop() {
  std::unique_lock<std::mutex> lck(queue_mutex_);
  stopped_ = true;
  queue_cv_.notify_all();
}

void EventQueue::BindWriter(grpc::ServerWriter<proto::Event>* writer,
                            std::mutex* mutex) {
  proto::Event event;
  while (Dequeue(&event)) {
    std::lock_guard<std::mutex> lock(*mutex);
    writer->Write(event);
  }
}

void EventQueue::BindWriterUnlocked(grpc::ServerWriter<proto::Event>* writer) {
  proto::Event event;
  while (Dequeue(&event)) writer->Write(event);
}
}  // namespace manager
