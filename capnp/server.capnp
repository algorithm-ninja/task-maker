@0xe218398f76d45e3a;

using import "file.capnp".FileSender;
using import "file.capnp".FileReceiver;
using import "sha256.capnp".SHA256;
using import "evaluation.capnp".Result;
using import "evaluation.capnp".Resources;
using import "evaluation.capnp".Evaluator;
using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("capnproto");

struct File {
  # This struct should not be modified by the client
  id @0 :UInt64;
  description @1 :Text;
  executable @2 :Bool;
}

interface Execution {
  # Add input dependencies
  setExecutablePath @0 (path :Text);
  setExecutable @1 (file :File);
  setStdin @2 (file :File);
  addInput @3 (name :Text, file :File);

  # Set arguments
  setArgs @4 (args :List(Text));

  # Set execution options
  disableCache @5 ();
  makeExclusive @6 ();
  setLimits @7 (limits: Resources);

  # Get file IDs representing outputs
  stdout @8 (isExecutable :Bool = false) -> (file :File);
  stderr @9 (isExecutable :Bool = false) -> (file :File);
  output @10 (name :Text, isExecutable :Bool = false) -> (file :File);

  # To be called to be notified of the start of the evaluation
  notifyStart @11 ();

  # The following methods will only complete (i.e. return or call callbacks)
  # when the evaluation is complete.
  getResult @12 () -> (result :Result);
}

interface FrontendContext {
  provideFile @0 (
    hash :SHA256,
    description :Text,
    isExecutable :Bool
  ) -> (file :File);
  addExecution @1 (description :Text) -> (execution :Execution);
  
  # The following methods should only be called after the computational
  # DAG is fully defined.
  startEvaluation @2 (sender :FileSender);
  getFileContents @3 (file :File, receiver :FileReceiver);
  stopEvaluation @4 ();
}

interface MainServer extends(FileSender) {
  registerFrontend @0 () -> (context: FrontendContext); # For the frontend
  registerEvaluator @1 (name :Text, evaluator :Evaluator) -> (); # For workers
}
