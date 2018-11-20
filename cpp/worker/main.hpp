#ifndef WORKER_MAIN_HPP
#define WORKER_MAIN_HPP
#include <kj/main.h>

namespace worker {

class Main {
 public:
  explicit Main(kj::ProcessContext* context) : context(*context) {}
  kj::MainBuilder::Validity Run();
  kj::MainFunc getMain();

 private:
  kj::ProcessContext& context;
};
}  // namespace worker
#endif
