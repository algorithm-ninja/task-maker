#!/usr/bin/env python3

import os
import string
from typing import List
from typing import Optional  # pylint: disable=unused-import
from typing import Tuple  # pylint: disable=unused-import

from bindings import Execution
from bindings import FileID  # pylint: disable=unused-import
from python.dispatcher import Dispatcher
from python.dispatcher import DispatcherCallback
from python.dispatcher import Event
from python.dispatcher import EventStatus
from python.language import Language
from python.ui import UI
from python.ui import CompilationStatus


def _sanitize(filename: str) -> str:
    return "".join(
        filter(lambda x: x in string.ascii_letters + string.digits + "_-.",
               filename))


class SourceFile:
    def __init__(self, dispatcher: Dispatcher, ui: UI, path: str,
                 is_solution: bool) -> None:
        # is_solution is true if the file to compile is a solution to be tested.
        self._path = path
        self._dispatcher = dispatcher
        self._basename = os.path.basename(path)
        self._compiled_name = _sanitize(os.path.splitext(self._basename)[0])
        self.compilation_output = None  # type: Optional[FileID]
        self._runtime_deps = []  # type: List[Tuple[str, FileID]]
        self._is_solution = is_solution
        self._stderr = None  # type: Optional[FileID]
        self._ui = ui

    def get_language(self) -> Language:
        return Language.from_file(self._path)

    def _callback(self, event: Event, status: EventStatus) -> bool:
        # Ignore load_files of dependencies.
        if self.get_language().needs_compilation() and isinstance(
                event, FileID):
            return True
        if status == EventStatus.START:
            self._ui.set_compilation_status(self._basename, self._is_solution,
                                            CompilationStatus.RUNNING)
            return True
        # At this point, if self._stderr is not None, we have real compilation
        # output.
        if self._stderr is not None:
            message = self._stderr.contents(1024 * 1024)  # type: Optional[str]
        else:
            message = None
        if status == EventStatus.FAILURE:
            self._ui.set_compilation_status(self._basename, self._is_solution,
                                            CompilationStatus.FAILURE, message)
            return self._is_solution
        if status == EventStatus.SUCCESS:
            self._ui.set_compilation_status(self._basename, self._is_solution,
                                            CompilationStatus.SUCCESS, message)
            return True
        raise RuntimeError("Unexpected compilation state")

    def compile(self, graders: List[str], cache_mode: Execution.CachingMode) -> None:

        self._ui.set_compilation_status(self._basename, self._is_solution,
                                        CompilationStatus.WAITING)
        if graders is None:
            graders = []
        lang = self.get_language()
        # No grader support for Python and shell - compilation is a noop.
        if not lang.needs_compilation():
            self.compilation_output = self._dispatcher.load_file(
                self._path, self._path, self._callback)
            self._runtime_deps = [(os.path.basename(dep),
                                   self._dispatcher.load_file(dep, dep))
                                  for dep in graders]
            return
        elif lang in [Language.CPP, Language.C]:
            if lang == Language.CPP:
                compilation_command = "/usr/bin/g++"
                compilation_args = ["-std=c++14"]
            else:
                compilation_command = "/usr/bin/gcc"
                compilation_args = ["-std=c11"]
            compilation_args += [
                "-O2", "-Wall", "-DEVAL", "-o", self._compiled_name
            ]
            files_to_pass = []  # type: List[Tuple[str, FileID]]
            for source_file in [self._path] + graders:
                # TODO(veluca): call callback?
                basename = _sanitize(os.path.basename(source_file))
                files_to_pass.append((basename, self._dispatcher.load_file(
                    source_file, source_file)))
                compilation_args.append(basename)

        # Once compilation commands are decided, the rest is the same for all
        # languages.
        execution = self._dispatcher.add_execution(
            "Compiling " + self._path, compilation_command, compilation_args,
            self._callback, exclusive=False, cache_mode=cache_mode)
        for name, file_id in files_to_pass:
            execution.input(name, file_id)
        # Set (very large) time and memory limits for compilation.
        execution.cpu_limit(10.0)
        execution.wall_limit(20.0)
        execution.memory_limit(2 * 1024 * 1024)  # 2 GiB
        self._stderr = execution.stderr()
        self.compilation_output = execution.output(self._compiled_name,
                                                   "Compiled " + self._path)

    def execute(self, description: str, args: List[str],
                callback: DispatcherCallback, exclusive: bool,
                cache_mode: Execution.CachingMode) -> Execution:
        if self.compilation_output is None:
            raise RuntimeError("You must compile this source file first")
        execution = self._dispatcher.add_execution(
            description, self._compiled_name, args, callback, exclusive, cache_mode)
        execution.input(self._compiled_name, self.compilation_output)
        for runtime_dep in self._runtime_deps:
            execution.input(runtime_dep[0], runtime_dep[1])
        # Return the execution to allow doing more complicated things like
        # setting time limits.
        return execution
