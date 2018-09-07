#include "sandbox/main.hpp"
#include "server/main.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/misc.hpp"
#include "util/version.hpp"
#include "worker/main.hpp"

class TaskMakerMain {
 public:
  TaskMakerMain(kj::ProcessContext& context) : context(context) {}
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
  worker::Main wm = context;
  server::Main sm = context;
  sandbox::Main bm = context;
};

KJ_MAIN(TaskMakerMain);
