#include "worker/main.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/misc.hpp"
#include "util/version.hpp"

class TaskMakerMain {
 public:
  TaskMakerMain(kj::ProcessContext& context) : context(context) {}
  kj::MainFunc getMain() {
    worker::Main wm(context);
    return kj::MainBuilder(context, "Task-Maker (" + util::version + ")",
                           "The new cmsMake!")
        .addOption({'d', "daemon"}, util::setBool(Flags::daemon),
                   "Become a daemon")
        .addOptionWithArg({'P', "pidfile"}, util::setString(Flags::pidfile),
                          "<PIDFILE>",
                          "Path where the pidfile should be stored")
        .addSubCommand("worker", KJ_BIND_METHOD(wm, getMain), "run the worker")
        .build();
  }

 private:
  kj::ProcessContext& context;
};

KJ_MAIN(TaskMakerMain);
