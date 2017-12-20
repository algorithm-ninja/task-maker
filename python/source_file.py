#!/usr/bin/env python3

import os
from typing import List
from typing import Optional  # pylint: disable=unused-import
from typing import Tuple  # pylint: disable=unused-import

from bindings import Execution
from bindings import FileID  # pylint: disable=unused-import
from python import dependency_finder
from python import sanitize
from python.dispatcher import Dispatcher
from python.dispatcher import DispatcherCallback
from python.dispatcher import Event
from python.dispatcher import EventStatus
from python.language import Language
from python.ui import CompilationStatus
from python.ui import UI


class SourceFile:
    @staticmethod
    def from_file(dispatcher: Dispatcher, ui: UI, path: str,
                  is_solution: bool) -> "SourceFile":
        lang = Language.from_file(path)
        if lang == Language.CPP:
            return CPP(dispatcher, ui, path, is_solution)
        elif lang == Language.C:
            return C(dispatcher, ui, path, is_solution)
        elif lang == Language.PY:
            return PY(dispatcher, ui, path, is_solution)
        elif lang == Language.SH:
            return SH(dispatcher, ui, path, is_solution)
        return SourceFile(dispatcher, ui, path, is_solution)

    def __init__(self, dispatcher: Dispatcher, ui: UI, path: str,
                 is_solution: bool) -> None:
        # is_solution is true if the file to compile is a solution to be tested.
        self._path = path
        self._dispatcher = dispatcher
        self._basename = os.path.basename(path)
        self._compiled_name = sanitize.sanitize_filename(
            os.path.splitext(self._basename)[0])
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

    def compile(self,
                graders: List[str],  # pylint: disable=unused-argument
                cache_mode: Execution.CachingMode  # pylint: disable=unused-argument
               ) -> None:
        self._ui.set_compilation_status(self._basename, self._is_solution,
                                        CompilationStatus.WAITING)
        # the subclass will create the real compilation

    def execute(self, description: str, args: List[str],
                callback: DispatcherCallback, exclusive: bool,
                cache_mode: Execution.CachingMode) -> Execution:
        if self.compilation_output is None:
            raise RuntimeError("You must compile this source file first")
        execution = self._dispatcher.add_execution(
            description, self._compiled_name, args, callback, exclusive,
            cache_mode)
        execution.input(self._compiled_name, self.compilation_output)
        for runtime_dep in self._runtime_deps:
            execution.input(runtime_dep[0], runtime_dep[1])
        # Return the execution to allow doing more complicated things like
        # setting time limits.
        return execution


class Compiled(SourceFile):
    def _compile(self, graders: List[str], cache_mode: Execution.CachingMode,
                 compilation_command: str, compilation_args: List[str]) -> None:
        super().compile(graders, cache_mode)
        files_to_pass = []  # type: List[Tuple[str, FileID]]
        for source_file in [self._path] + graders:
            basename = sanitize.sanitize_filename(
                os.path.basename(source_file))
            files_to_pass.append((basename, self._dispatcher.load_file(
                source_file, source_file)))
            compilation_args.append(basename)

        dependencies = dependency_finder.find_dependency(self._path)
        for dependency in dependencies:
            files_to_pass.append((dependency.name, self._dispatcher.load_file(
                dependency.path, dependency.path)))

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

# pylint: disable=invalid-name


class CPP(Compiled):
    def compile(self, graders: List[str],
                cache_mode: Execution.CachingMode) -> None:
        self._compile(
            graders,
            cache_mode,
            "/usr/bin/g++",
            ["-std=c++14", "-O2", "-Wall", "-DEVAL", "-o", self._compiled_name])


class C(Compiled):
    def compile(self, graders: List[str],
                cache_mode: Execution.CachingMode) -> None:
        self._compile(
            graders,
            cache_mode,
            "/usr/bin/gcc",
            ["-std=c11", "-O2", "-Wall", "-DEVAL", "-o", self._compiled_name])


class PY(Compiled):
    ERROR_CMD = ["-c",
                 "echo 'Missing shebang!\nAdd #!/usr/bin/env python' >&2",
                 "&&", "false"]

    def compile(self, graders: List[str],
                cache_mode: Execution.CachingMode) -> None:
        super().compile(graders, cache_mode)
        with open(self._path) as source:
            if source.read(2) != "#!":
                self._compile(graders, cache_mode, "/bin/bash", self.ERROR_CMD)
                return
        self.compilation_output = self._dispatcher.load_file(
            self._path, self._path, self._callback)
        self._runtime_deps = [(os.path.basename(dep),
                               self._dispatcher.load_file(dep, dep))
                              for dep in graders]


class SH(PY):
    ERROR_CMD = ["-c",
                 "echo 'Missing shebang!\nAdd #!/usr/bin/env bash' >&2",
                 "&&", "false"]
