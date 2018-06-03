#ifndef UTIL_IPC_HPP
#define UTIL_IPC_HPP
#include <pthread.h>
#include <string.h>
#include <sys/mman.h>
#include <stdexcept>
//#include <type_traits>

#ifndef MAP_ANONYMOUS
#define MAP_ANONYMOUS MAP_ANON
#endif

template <typename T>
class SharedQueue {
  template <typename U>
  static void SetUp(U*& u, char*& cur) {
    u = (U*)cur;
    cur += sizeof(U);
  }

  static constexpr size_t MemSize(size_t size) {
    return sizeof(pthread_mutex_t) + 2 * sizeof(pthread_cond_t) +
           sizeof(size_t) + sizeof(bool) + size * sizeof(T);
  }

 public:
  SharedQueue(size_t size) : size_(size) {
    // static_assert(std::is_trivially_copyable<T>::value,
    //              "T must be trivially copiable!");
    shm_ = (char*)mmap(nullptr, MemSize(size), PROT_READ | PROT_WRITE,
                       MAP_ANONYMOUS | MAP_SHARED, -1, 0);
    if (shm_ == MAP_FAILED)
      throw std::runtime_error(std::string("mmap: ") + strerror(errno));
    char* cur = shm_;
    SetUp(mutex_, cur);
    SetUp(empty_, cur);
    SetUp(full_, cur);
    SetUp(current_size_, cur);
    SetUp(stopping_, cur);
    SetUp(data_, cur);
    *current_size_ = 0;
    *stopping_ = false;
    // Initialize synchronization structures.
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED);
    pthread_mutex_init(mutex_, &attr);
    pthread_mutexattr_destroy(&attr);
    pthread_condattr_t cattr;
    pthread_condattr_init(&cattr);
    pthread_condattr_setpshared(&cattr, PTHREAD_PROCESS_SHARED);
    pthread_cond_init(empty_, &cattr);
    pthread_cond_init(full_, &cattr);
    pthread_condattr_destroy(&cattr);
  }

  ~SharedQueue() {
    // Should we destroy the mutex and CVs too?
    munmap(shm_, MemSize(size_));
  }

  // Blocks until there is something to dequeue, returns false if stopped
  bool Dequeue(T* out) {
    pthread_mutex_lock(mutex_);
    while (*current_size_ == 0 && !*stopping_) {
      pthread_cond_wait(empty_, mutex_);
    }
    if (*stopping_) {
      pthread_mutex_unlock(mutex_);
      return false;
    }
    (*current_size_)--;
    memcpy(out, &data_[*current_size_], sizeof(T));
    pthread_cond_broadcast(full_);
    pthread_mutex_unlock(mutex_);
    return true;
  }

  // Blocks if the queue is full, returns false if stopped
  bool Enqueue(const T& in) {
    pthread_mutex_lock(mutex_);
    while (*current_size_ == size_ && !*stopping_) {
      pthread_cond_wait(full_, mutex_);
    }
    if (*stopping_) {
      pthread_mutex_unlock(mutex_);
      return false;
    }
    memcpy(&data_[*current_size_], &in, sizeof(T));
    (*current_size_)++;
    pthread_cond_broadcast(empty_);
    pthread_mutex_unlock(mutex_);
    return true;
  }

  void Stop() {
    pthread_mutex_lock(mutex_);
    *stopping_ = true;
    pthread_cond_broadcast(empty_);
    pthread_cond_broadcast(full_);
    pthread_mutex_unlock(mutex_);
  }

  SharedQueue(const SharedQueue&) = delete;
  SharedQueue& operator=(const SharedQueue&) = delete;
  SharedQueue(SharedQueue&&) = delete;
  SharedQueue& operator=(SharedQueue&&) = delete;

 private:
  size_t size_;
  char* shm_;
  pthread_mutex_t* mutex_;
  pthread_cond_t* empty_;
  pthread_cond_t* full_;
  size_t* current_size_;
  bool* stopping_;
  T* data_;
};

#endif
