#include "server/main.hpp"
#include <thread>

#include <capnp/ez-rpc.h>

#include "server/server.hpp"
#include "util/daemon.hpp"
#include "util/flags.hpp"
#include "util/misc.hpp"
#include "util/version.hpp"

namespace server {
kj::MainBuilder::Validity Main::Run() {
  if (Flags::daemon) {
    util::daemonize(Flags::pidfile);
  }
  capnp::EzRpcServer server(kj::heap<server::Server>(), Flags::listen_address,
                            Flags::port);
  kj::NEVER_DONE.wait(server.getWaitScope());
}

kj::MainFunc Main::getMain() {
  return kj::MainBuilder(context, "Task-Maker Server (" + util::version + ")",
                         "Receives evaluations and dispatches them to workers")
      .addOptionWithArg({'l', "address"},
                        util::setString(Flags::listen_address), "<ADDRESS>",
                        "Address to connect to")
      .addOptionWithArg({'p', "port"}, util::setInt(Flags::port), "<PORT>",
                        "Port to listen on")
      .callAfterParsing(KJ_BIND_METHOD(*this, Run))
      .build();
}
}  // namespace server
