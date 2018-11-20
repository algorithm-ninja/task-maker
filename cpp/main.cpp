#include "sandbox/main.hpp"
#include "server/main.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/misc.hpp"
#include "util/version.hpp"
#include "worker/main.hpp"

class TaskMakerMain {
 public:
  // NOLINTNEXTLINE(google-runtime-references)
  explicit TaskMakerMain(kj::ProcessContext& context)
      : context(context), wm(&context), sm(&context), bm(&context) {}
  kj::MainFunc getMain() {
    return kj::MainBuilder(context, "Task-Maker (" + util::version + ")",
                           "The new cmsMake!")
        .addSubCommand("worker", KJ_BIND_METHOD(wm, getMain), "run the worker")
        .addSubCommand("server", KJ_BIND_METHOD(sm, getMain), "run the server")
        .addSubCommand("sandbox", KJ_BIND_METHOD(bm, getMain),
                       "run the sandbox")
        .build();
  }

 private:
  kj::ProcessContext& context;
  worker::Main wm;
  server::Main sm;
  sandbox::Main bm;
};

KJ_MAIN(TaskMakerMain);
