#!/usr/bin/env python3
import time

from task_maker.args import CacheMode
from task_maker.config import Config
from task_maker.task_maker_frontend import Frontend, File, Resources, Fifo, \
    Result
from typing import Union, List, Callable, Optional, Dict, Iterable


class ExecutionPool:
    def __init__(self, config: Config, frontend: Frontend):
        self.config = config
        self.frontend = frontend
        self.running = dict()  # type: Dict[Execution, float]

    def execution_start(self, execution: "Execution"):
        self.running[execution] = time.monotonic()

    def execution_done(self, execution: "Execution"):
        if execution in self.running:
            del self.running[execution]

    def start(self):
        self.frontend.evaluate()


class Execution:
    def __init__(self,
                 name: str,
                 pool: ExecutionPool,
                 cmd: Union[File, str],
                 args: List[str],
                 ui_print_func: Optional[Callable],
                 ui_print_data: Dict,
                 *,
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
                 inputs: Dict[str, File] = None,
                 outputs: Iterable[str] = ()):
        self.name = name
        self.pool = pool
        self.cmd = cmd
        self.args = args
        self.ui_print_func = ui_print_func
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

        self.stdout = None  # type: Optional[File]
        self.stderr = None  # type: Optional[File]
        self._stdout = None  # type: Optional[str]
        self._stderr = None  # type: Optional[str]
        self._outputs = dict()  # type: Dict[str, File]

        self._on_start_cb = None  # type: Optional[Callable]
        self._on_done_db = None  # type: Optional[Callable]
        self._on_skip_cb = None  # type: Optional[Callable]

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
        if isinstance(self.cmd, File):
            self._execution.setExecutable("Executable of %s" % self.name,
                                          self.cmd)
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
        if not inputs:
            inputs = dict()
        for path, file in inputs.items():
            self._execution.addInput(path, file)
        for path in outputs:
            self._outputs[path] = self._execution.output(path)

        if self.store_stdout:
            self.stdout.getContentsAsString(self._get_stdout_internal)
        if self.store_stderr:
            self.stderr.getContentsAsString(self._get_stderr_internal)

        self._execution.notifyStart(self._notify_start_internal)
        # getResult should be the last thing done
        self._execution.getResult(self._get_result_internal,
                                  self._skipped_internal)

    def _notify_start_internal(self):
        # TODO write to log
        self.pool.execution_start(self)
        if self._on_start_cb:
            self._on_start_cb()

    def _get_result_internal(self, result: Result):
        # TODO write to log
        self.pool.execution_done(self)
        self._result = result
        if self._on_done_db:
            self._on_done_db(result)

    def _skipped_internal(self):
        # TODO write to log
        if self._on_skip_cb:
            self._on_skip_cb()

    def _get_stdout_internal(self, stdout: str):
        self._stdout = stdout

    def _get_stderr_internal(self, stderr: str):
        self._stderr = stderr

    @property
    def stdout_content(self):
        return self._stdout

    @property
    def stderr_content(self):
        return self._stderr

    def output(self, path: str) -> File:
        if path not in self._outputs:
            raise ValueError("%s is not registered as an output" % path)
        return self._outputs[path]

    @property
    def result(self):
        return self._result
