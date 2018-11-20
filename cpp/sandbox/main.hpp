#ifndef SANDBOX_MAIN_HPP
#define SANDBOX_MAIN_HPP
#include <kj/main.h>
#include "sandbox/sandbox.hpp"

namespace sandbox {

class Main {
 public:
  explicit Main(kj::ProcessContext* context) : context(*context) {}
  kj::MainBuilder::Validity Run();
  kj::MainFunc getMain();

 private:
  kj::ProcessContext& context;
  bool read_binary = false;
};
}  // namespace sandbox
#endif
