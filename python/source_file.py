#!/usr/bin/env python3

import os
from typing import List
from typing import Optional  # pylint: disable=unused-import
from typing import Tuple  # pylint: disable=unused-import

from bindings import Execution
from bindings import FileID  # pylint: disable=unused-import
from python.dispatcher import Dispatcher
from python.dispatcher import DispatcherCallback
from python.language import Language


class SourceFile:
    def __init__(self, dispatcher: Dispatcher, path: str) -> None:
        self._path = path
        self._dispatcher = dispatcher
        self._compiled_name = os.path.splitext(os.path.basename(path))[0]
        self._compilation_output = None  # type: Optional[FileID]

    def get_language(self) -> Language:
        return Language.from_file(self._path)

    def compile(self, graders: List[str],
                callback: DispatcherCallback) -> FileID:
        if graders is None:
            graders = []
        lang = self.get_language()
        # No grader support for Python and shell - compilation is a noop.
        if not lang.needs_compilation():
            self._compilation_output = self._dispatcher.load_file(
                self._path, self._path, callback)
            return self._compilation_output
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
                basename = os.path.basename(source_file)
                files_to_pass.append((basename, self._dispatcher.load_file(
                    source_file, source_file)))
                compilation_args += basename

        # Once compilation commands are decided, the rest is the same for all
        # languages.
        execution = self._dispatcher.add_execution("Compiling " + self._path,
                                                   compilation_command,
                                                   compilation_args, callback)
        for name, file_id in files_to_pass:
            execution.input(name, file_id)
        # Set (very large) time and memory limits for compilation.
        execution.cpu_limit(10.0)
        execution.wall_limit(20.0)
        execution.memory_limit(2 * 1024 * 1024)  # 2 GiB
        return execution.output(self._compiled_name, "Compiled " + self._path)

    def execute(self, description: str, args: List[str],
                callback: DispatcherCallback) -> Execution:
        if self._compilation_output is None:
            raise RuntimeError("You must compile this source file first")
        execution = self._dispatcher.add_execution(
            description, self._compiled_name, args, callback)
        execution.input(self._compiled_name, self._compilation_output)
        # Return the execution to allow doing more complicated things like
        # setting time limits.
        return execution
