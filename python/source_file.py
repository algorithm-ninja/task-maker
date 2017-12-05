#!/usr/bin/env python3

import os

from python.language import Language


class SourceFile:
    def __init__(self, dispatcher, path):
        self._path = path
        self._dispatcher = dispatcher
        self._compiled_name = os.path.splitext(os.path.basename(path))[0]

    def get_language(self):
        return Language.from_file(self._path)

    def compile(self, graders, cb):
        if graders is None:
            graders = []
        lang = self.get_language()
        # No grader support for Python and shell - compilation is a noop.
        if not lang.needs_compilation():
            return self._dispatcher.load_file(self._path, self._path, cb)
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
            files_to_pass = []
            for sf in [self._path] + graders:
                # TODO(veluca): call callback?
                basename = os.path.basename(sf)
                files_to_pass.append(basename,
                                     self._dispatcher.load_file(sf, sf))
                compilation_args += basename

        # Once compilation commands are decided, the rest is the same for all
        # languages.
        execution = dispatcher.add_execution("Compiling " + self._path,
                                             compilation_command,
                                             compilation_args, cb)
        for name, file_id in files_to_pass:
            execution.input(name, file_id)
        # Set (very large) time and memory limits for compilation.
        execution.cpu_limit(10.0)
        execution.wall_limit(20.0)
        execution.memory_limit(2 * 1024 * 1024)  # 2 GiB
        return execution.output(self._compiled_name, "Compiled " + self._path)

    def execute(self, description, compilation_output, args, cb):
        execution = self._dispatcher.add_execution(
            description, self._compiled_name, args, cb)
        execution.input(self._compiled_name, compilation_output)
        # Return the execution to allow doing more complicated things like
        # setting time limits.
        return execution
