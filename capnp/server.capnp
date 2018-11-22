@0xe218398f76d45e3a;

using import "file.capnp".FileSender;
using import "file.capnp".FileReceiver;
using import "sha256.capnp".SHA256;
using import "evaluation.capnp".ProcessResult;
using import "evaluation.capnp".Resources;
using import "evaluation.capnp".Evaluator;
using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("capnproto");

struct File {
  # This struct should not be modified by the client
  id @0 :UInt64;
}

struct Fifo {
  # This struct should not be modified by the client
  id @0 :UInt64;
}

interface Execution {
  # Add input dependencies
  setExecutablePath @0 (path :Text);
  setExecutable @1 (name :Text, file :File);
  setStdin @2 (file :File);
  addInput @3 (name :Text, file :File);

  # Set arguments
  setArgs @4 (args :List(Text));

  # Set execution options
  disableCache @5 ();
  makeExclusive @6 ();
  setLimits @7 (limits: Resources);
  setExtraTime @8 (extraTime: Float32);

  # Get file IDs representing outputs
  getStdout @9 (isExecutable :Bool = false) -> (file :File);
  getStderr @10 (isExecutable :Bool = false) -> (file :File);
  getOutput @11 (name :Text, isExecutable :Bool = false) -> (file :File);

  # Add a FIFO
  setStdinFifo @12(fifo :Fifo);
  setStdoutFifo @13 (fifo :Fifo);
  setStderrFifo @14 (fifo :Fifo);
  addFifo @15 (name :Text, fifo :Fifo);

  # To be called to be notified of the start of the evaluation
  notifyStart @16 ();

  # The following methods will only complete (i.e. return or call callbacks)
  # when the evaluation is complete.
  getResult @17 () -> (result :ProcessResult);
}

interface ExecutionGroup {
  addExecution @0 (description :Text) -> (execution :Execution);
  createFifo @1 () -> (fifo :Fifo);
}

interface FrontendContext {
  provideFile @0 (
    hash :SHA256,
    description :Text,
    isExecutable :Bool
  ) -> (file :File);
  addExecution @1 (description :Text) -> (execution :Execution);
  addExecutionGroup @2 (description :Text) -> (group :ExecutionGroup);
  
  # The following methods should only be called after the computational
  # DAG is fully defined.
  startEvaluation @3 (sender :FileSender);
  getFileContents @4 (file :File, receiver :FileReceiver);
  stopEvaluation @5 ();
}

interface MainServer extends(FileSender) {
  registerFrontend @0 () -> (context: FrontendContext); # For the frontend
  registerEvaluator @1 (name :Text, evaluator :Evaluator) -> (); # For workers
}
