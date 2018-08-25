#include "sandbox/main.hpp"
#include <capnp/ez-rpc.h>
#include <thread>

#include <kj/io.h>
#include "capnp/server.capnp.h"
#include "util/misc.hpp"
#include "util/version.hpp"

namespace sandbox {
kj::MainBuilder::Validity Main::Run() {
  kj::FdInputStream in(fileno(stdin));
  ExecutionOptions options("", "");
  if (read_binary) {
    in.read(&options, sizeof(options), sizeof(options));
  } else {
    KJ_FAIL_ASSERT("Not implemented");
  }
  sandbox::ExecutionInfo outcome;
  std::string error_msg;
  std::unique_ptr<sandbox::Sandbox> sb = sandbox::Sandbox::Create();
  kj::FdOutputStream out(fileno(stdout));
  bool ok = sb->Execute(options, &outcome, &error_msg);
  if (read_binary) {
    if (!ok) {
      size_t sz = error_msg.size();
      out.write(&sz, sizeof(sz));
      out.write(error_msg.c_str(), sz + 1);
    } else {
      size_t sz = 0;
      out.write(&sz, sizeof(sz));
      out.write(&outcome, sizeof(outcome));
      // TODO: think about outcome.message
    }
  } else {
    KJ_FAIL_ASSERT("Not implemented");
  }
  return true;
}

kj::MainFunc Main::getMain() {
  return kj::MainBuilder(context, "Task-Maker Worker (" + util::version + ")",
                         "Executes requests pulled from a server")
      .addOption({'b', "bin"}, util::setBool(read_binary),
                 "Read/write options/results in binary.")
      // TODO: allow to specify options from the command line
      .callAfterParsing(KJ_BIND_METHOD(*this, Run))
      .build();
}
}  // namespace sandbox
