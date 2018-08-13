#ifndef WORKER_MANAGER_HPP
#define WORKER_MANAGER_HPP
#include <stdlib.h>

namespace worker {

// TODO: keep track of errors in the worker processes and quit
// if they are too frequent.
class Manager {
 public:
  static void Start();
  static void Stop();
  static void ChangeNumWorker(size_t num);
};

}  // namespace worker
#endif
