@0xe218398f76d45e3a;

using import "file.capnp".FileSender;
using import "file.capnp".FileReceiver;
using import "sha256.capnp".SHA256;
using import "evaluation.capnp".Result;
using import "evaluation.capnp".Resources;
using import "evaluation.capnp".Evaluator;

struct File {
  id @0 :UInt64;
  description @1 :Text;
}

interface Execution {
  # Add input dependencies
  setExecutablePath @0 (path :Text);
  setExecutable @1 (file :File);
  setStdin @2 (file :File);
  addInput @3 (name :Text, file :File);

  # Get file IDs representing outputs
  stdout @4 (isExecutable :Bool = false) -> (output :File);
  stderr @5 (isExecutable :Bool = false) -> (output :File);
  output @6 (name :Text, isExecutable :Bool = false) -> (output :File);

  # Set execution options
  disableCache @7 ();
  forceCache @8 ();
  makeExclusive @9 ();
  setLimits @10 (limits: Resources);

  # The following methods will only complete (i.e. return or call callbacks)
  # when the evaluation is complete.
  getResult @11 () -> (result :Result);
}

interface FrontendContext {
  provideFile @0 (
    hash :SHA256,
    description :Text,
    isExecutable :Bool
  ) -> (input :File);
  addExecution @1 (description :Text) -> (execution :Execution);
  
  # The following methods should only be called after the computational
  # DAG is fully defined.
  startEvaluation @2 (sender :FileSender);
  getFileContents @3 (file :File, receiver :FileReceiver);
  stopEvaluation @4 ();
}

interface MainServer extends(FileSender) {
  registerFrontend @0 () -> (context: FrontendContext); # For the frontend
  registerEvaluator @1 (evaluator :Evaluator) -> (); # For workers
}
