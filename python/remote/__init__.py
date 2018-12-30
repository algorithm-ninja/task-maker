#!/usr/bin/env python3

import time

import signal
from task_maker.args import CacheMode
from task_maker.config import Config
from task_maker.languages import CommandType
from task_maker.task_maker_frontend import Frontend, File, Resources, Fifo, \
    Result, ResultStatus, ExecutionGroup
from task_maker.utils import result_to_dict
from typing import Union, List, Callable, Optional, Dict, Iterable, Tuple, Any


class ExecutionPool:
    """
    Pool of execution, it will manage the starting and stopping of the frontend
    and the list of running executions.
    """

    def __init__(self, config: Config, frontend: Frontend,
                 ui_printer: "UIPrinter"):
        self.config = config
        self.frontend = frontend
        self.ui_printer = ui_printer
        self.running = dict()  # type: Dict[Execution, float]
        self.stopped = False

    def execution_start(self, execution: "Execution"):
        """
        When the `execution` starts this methods should be called
        """
        self.running[execution] = time.monotonic()

    def execution_done(self, execution: "Execution"):
        """
        When the `execution` ends this methods should be called
        """
        if execution in self.running:
            del self.running[execution]

    def start(self):
        """
        Start the evaluation of all the registered executions, registering a
        signal handler for SIGINT and SIGTERM, stopping the executions on those
        signals.
        """

        def stop_server(_1: int, _2: Any) -> None:
            self.stop()

        signal.signal(signal.SIGINT, stop_server)
        signal.signal(signal.SIGTERM, stop_server)

        self.frontend.evaluate()

    def stop(self):
        """
        Stop the current evaluation
        """
        self.frontend.stopEvaluation()
        self.stopped = True


class Execution:
    """
    Wrapper around the frontend. This class should be used instead of the
    frontend one, it's much more safe because all the setup is done in the
    correct order.
    """

    def __init__(self,
                 name: str,
                 pool: ExecutionPool,
                 cmd: Union[Tuple[File, str], "SourceFile", str],
                 args: List[str],
                 ui_print_tag: str,
                 ui_print_data: Dict,
                 *,
                 group: Optional[ExecutionGroup] = None,
                 cache_on: Iterable[CacheMode] = (CacheMode.ALL,
                                                  CacheMode.REEVALUATE),
                 extra_time: float = 0.0,
                 limits: Optional[Resources] = None,
                 can_exclusive: bool = False,
                 stdin: Union[File, Fifo, str, None] = None,
                 stdout_fifo: Union[Fifo, None] = None,
                 stderr_fifo: Union[Fifo, None] = None,
                 store_stdout: bool = False,
                 store_stderr: bool = False,
                 store_stdout_bytes: bool = False,
                 store_stderr_bytes: bool = False,
                 stdout_limit: int = 0xffffffffffffffff,
                 stderr_limit: int = 0xffffffffffffffff,
                 inputs: Dict[str, File] = None,
                 outputs: Iterable[Union[str, Tuple[str, bool]]] = ()):
        """
        :param name: Description of the execution
        :param pool: ExecutionPool to bind to
        :param cmd: Command to execute, it can be a pair (file, name), an
        already prepared SourceFile or the name of a system executable
        :param args: Args to supply to the program
        :param ui_print_tag: Tag to put in the json ui
        :param ui_print_data: Additional data to put in the json response
        :param group: Optional ExecutionGroup to put this execution into
        :param cache_on: List of CacheModes on which the cache will be used
        :param extra_time: If limits is set an extra time is gave to the
        execution
        :param limits: Limitations given to the execution
        :param can_exclusive: Whether --exclusive should be considered
        :param stdin: What to pass to stdin to the execution, it can be Fifo, a
        File or the content of a file
        :param stdout_fifo: The Fifo to pipe in the data from stdout.
        store_stdout must be False
        :param stderr_fifo: The Fifo to pipe in the data from stderr.
        store_stdout must be False
        :param store_stdout: Whether to store the content of stdout inside this
        class
        :param store_stderr: Whether to store the content of stderr inside this
        class
        :param inputs: A dictionary with the mapping path -> File to put inside
        the sandbox
        :param outputs: A list with the path to the files that should be
        generated
        """
        self.name = name
        self.pool = pool
        self.cmd = cmd
        self.args = args
        self.ui_print_tag = ui_print_tag
        self.ui_print_data = ui_print_data
        self.cache_on = cache_on
        self.extra_time = extra_time
        self.limits = limits
        self.can_exclusive = can_exclusive
        self.stdin = stdin
        self.stdout_fifo = stdout_fifo
        self.stderr_fifo = stderr_fifo
        self.store_stdout = store_stdout
        self.store_stderr = store_stderr
        self.store_stdout_bytes = store_stdout_bytes
        self.store_stderr_bytes = store_stderr_bytes

        self.stdout = None  # type: Optional[File]
        self.stderr = None  # type: Optional[File]
        self._stdout = None  # type: Optional[str]
        self._stderr = None  # type: Optional[str]
        self._stdout_bytes = None  # type: Optional[bytes]
        self._stderr_bytes = None  # type: Optional[bytes]
        self._outputs = dict()  # type: Dict[str, File]
        if not inputs:
            inputs = dict()

        self._on_start_cb = None  # type: Optional[Callable]
        self._on_done_cb = None  # type: Optional[Callable]
        self._on_skip_cb = None  # type: Optional[Callable]

        if group:
            self._execution = group.addExecution(name)
        else:
            self._execution = self.pool.frontend.addExecution(name)
        self._result = None  # type: Optional[Result]

        # execution generic settings
        if self.pool.config.cache not in self.cache_on:
            self._execution.disableCache()
        if self.can_exclusive and self.pool.config.exclusive:
            self._execution.makeExclusive()
        if self.limits is not None:
            self._execution.setLimits(self.limits)
        if self.extra_time:
            self._execution.setExtraTime(self.extra_time)

        # setup the command to execute
        if isinstance(self.cmd, tuple):
            name, file = self.cmd
            self._execution.setExecutable(name, self.cmd)
        # this is an hack because we cannot import SourceFile in here because of
        # a circular dependency
        elif str(type(
                self.cmd)) == "<class 'task_maker.source_file.SourceFile'>":
            if not self.cmd.prepared:
                raise ValueError("The SourceFile of cmd is not prepared")
            source_file = self.cmd
            cmd_type, (cmd, *self.args) = \
                source_file.language.get_execution_command(
                    source_file.exe_name, self.args, source_file.unit_name)
            if cmd_type == CommandType.LOCAL_FILE:
                self._execution.setExecutable(cmd, source_file.executable)
            else:
                self._execution.setExecutablePath(cmd)
                inputs[source_file.exe_name] = source_file.executable
            if not source_file.language.need_compilation:
                for dep in source_file.dependencies:
                    inputs[dep.name] = self.pool.frontend.provideFile(
                        dep.path, dep.path, False)
        elif isinstance(self.cmd, str):
            self._execution.setExecutablePath(self.cmd)
        else:
            raise ValueError(
                "cmd can be either a File or a str, not a %s" % type(self.cmd))
        self._execution.setArgs(self.args)

        # setup stdin
        if isinstance(self.stdin, File):
            self._execution.setStdin(self.stdin)
        elif isinstance(self.stdin, Fifo):
            self._execution.setStdinFifo(self.stdin)
        elif isinstance(self.stdin, str):
            file = self.pool.frontend.provideFileContent(
                self.stdin, "Stdin of %s" % self.name)
            self._execution.setStdin(file)
        elif self.stdin is not None:
            raise ValueError(
                "stdin can be either File, Fifo, str or None, not %s" % type(
                    self.stdin))

        # setup stdout and stderr
        if self.store_stdout and self.stdout_fifo is not None:
            raise ValueError("Cannot store stdout and use a Fifo")
        if self.store_stderr and self.stderr_fifo is not None:
            raise ValueError("Cannot store stderr and use a Fifo")
        if self.stdout_fifo is not None:
            self._execution.setStdoutFifo(self.stdout_fifo)
        else:
            self.stdout = self._execution.stdout()
        if self.stderr_fifo is not None:
            self._execution.setStderrFifo(self.stderr_fifo)
        else:
            self.stderr = self._execution.stderr()

        # setup other inputs and outputs
        for path, file in inputs.items():
            if isinstance(file, File):
                self._execution.addInput(path, file)
            elif isinstance(file, Fifo):
                self._execution.addFifo(path, file)
            else:
                raise ValueError("Unsupported input type %s" % type(file))
        for path in outputs:
            executable = False
            if isinstance(path, tuple):
                path, executable = path
            self._outputs[path] = self._execution.output(path, executable)

        if self.store_stdout:
            self.stdout.getContentsAsString(self._get_stdout_internal,
                                            stdout_limit)
        if self.store_stderr:
            self.stderr.getContentsAsString(self._get_stderr_internal,
                                            stderr_limit)
        if self.store_stdout_bytes:
            self.stdout.getContentsAsBytes(self._get_stdout_bytes_internal,
                                           stdout_limit)
        if self.store_stderr_bytes:
            self.stderr.getContentsAsBytes(self._get_stderr_bytes_internal,
                                           stderr_limit)

        self._execution.notifyStart(self._notify_start_internal)
        # getResult should be the last thing done on _execution
        self._execution.getResult(self._get_result_internal,
                                  self._skipped_internal)
        self.pool.ui_printer.print(self.name, self.ui_print_tag, "WAITING",
                                   self.ui_print_data, False)

    def _notify_start_internal(self):
        self.pool.ui_printer.print(self.name, self.ui_print_tag, "START",
                                   self.ui_print_data, False)
        self.pool.execution_start(self)
        if self._on_start_cb:
            self._on_start_cb()

    def _get_result_internal(self, result: Result):
        if result.status == ResultStatus.SUCCESS:
            state = "SUCCESS"
        else:
            state = "FAILURE"
        self.pool.ui_printer.print(self.name, self.ui_print_tag, state, {
            "result": result_to_dict(result),
            **self.ui_print_data
        }, result.was_cached)
        self.pool.execution_done(self)
        self._result = result
        self._on_done_internal()

    def _skipped_internal(self):
        self.pool.ui_printer.print(self.name, self.ui_print_tag, "SKIPPED",
                                   self.ui_print_data, False)
        if self._on_skip_cb:
            self._on_skip_cb()

    def _get_stdout_internal(self, stdout: str):
        self._stdout = stdout
        self._on_done_internal()

    def _get_stderr_internal(self, stderr: str):
        self._stderr = stderr
        self._on_done_internal()

    def _get_stdout_bytes_internal(self, stdout: bytes):
        self._stdout_bytes = stdout
        self._on_done_internal()

    def _get_stderr_bytes_internal(self, stderr: bytes):
        self._stderr_bytes = stderr
        self._on_done_internal()

    def _on_done_internal(self):
        if not self._on_done_cb:
            return
        if self.store_stdout and self._stdout is None:
            return
        if self.store_stderr and self._stderr is None:
            return
        if self.store_stdout_bytes and self._stdout_bytes is None:
            return
        if self.store_stderr_bytes and self._stderr_bytes is None:
            return
        if self.result is None:
            return
        self._on_done_cb(self.result)

    @property
    def stdout_content(self) -> str:
        """
        The content of stdout, must be called after the execution has completed
        and only if store_stdout has been set to True
        """
        if not self.store_stdout:
            raise ValueError("Stdout was not captured")
        if not self.result:
            raise RuntimeError("stdout_content must be called after "
                               "the execution has completed")
        return self._stdout

    @property
    def stderr_content(self) -> str:
        """
        The content of stderr, must be called after the execution has completed
        and only if store_stderr has been set to True
        """
        if not self.store_stderr:
            raise ValueError("Stderr was not captured")
        if not self.result:
            raise RuntimeError("stderr_content must be called after "
                               "the execution has completed")
        return self._stderr

    @property
    def stdout_content_bytes(self) -> bytes:
        """
        The content of stdout as bytes, must be called after the execution has
        completed and only if store_stdout_bytes has been set to True
        """
        if not self.store_stdout_bytes:
            raise ValueError("Stdout was not captured as bytes")
        if not self.result:
            raise RuntimeError("stdout_content_bytes must be called after "
                               "the execution has completed")
        return self._stdout_bytes

    @property
    def stderr_content_bytes(self) -> bytes:
        """
        The content of stderr as bytes, must be called after the execution has
        completed and only if store_stderr_bytes has been set to True
        """
        if not self.store_stderr_bytes:
            raise ValueError("Stderr was not captured as bytes")
        if not self.result:
            raise RuntimeError("stderr_content_bytes must be called after "
                               "the execution has completed")
        return self._stderr_bytes

    def output(self, path: str) -> File:
        """
        The file generated by the execution on that path. Must be called after
        the execution has completed.
        """
        if path not in self._outputs:
            raise ValueError("%s is not registered as an output" % path)
        return self._outputs[path]

    @property
    def result(self) -> Result:
        return self._result

    def bind(self,
             on_done_cb: Callable[[Result], None],
             on_start_cb: Callable[[], None] = None,
             on_skip_cb: Callable[[], None] = None):
        """
        Bind the callbacks that will be called when the execution starts,
        completes or is skipped
        """
        self._on_done_cb = on_done_cb
        self._on_start_cb = on_start_cb
        self._on_skip_cb = on_skip_cb
