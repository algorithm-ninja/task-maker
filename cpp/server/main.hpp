#ifndef SERVER_MAIN_HPP
#define SERVER_MAIN_HPP
#include <kj/main.h>

namespace server {

class Main {
 public:
  Main(kj::ProcessContext& context) : context(context) {}
  kj::MainBuilder::Validity Run();
  kj::MainFunc getMain();

 private:
  kj::ProcessContext& context;
};
}  // namespace server
#endif
