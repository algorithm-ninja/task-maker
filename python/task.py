#!/usr/bin/env python3

from enum import Enum

from python.language import Language


class ScoreMode(Enum):
    SUM = 0
    MIN = 1
    MUL = 2


class Input:
    def __init__(self, generator=None, args=None, path=None, validator=None):
        if (generator is None) == (path is None):
            raise ValueError(
                "You need to specify exactly a generator or a path")
        if (generator is None) != (args is None):
            raise ValueError(
                "Args should be specified together with a generator")
        if (path is None) and (validator is None):
            raise ValueError("You should validate generated inputs")
        self.should_generate = generator is not None
        self.generator = generator
        self.args = args
        self.path = path
        self.validator = validator


class Testcase:
    def __init__(self, input_file, output=None):
        # If the output is None, it will be generated with the official
        # solution. Otherwise it must be the path to the correct output
        # file.
        if not isinstance(input_file, Input):
            raise ValueError("The input file should be an instance of Input")
        if output is not None and not isinstance(output, str):
            raise ValueError(
                "The output should be either none or a path to a file")
        if input_file.path is None and output is not None:
            raise ValueError(
                "You should not provide an output for generated inputs")
        self.input = input_file
        self.output = output


class Subtask:
    def __init__(self, num, score, score_mode, tc_begin, tc_end):
        self.num = num
        self.score = score
        self.score_mode = score_mode
        if tc_begin >= tc_end or tc_begin < 0:
            raise ValueError("Invalid testcase range given")
        self.tc_range = (tc_begin, tc_end)


class Task:
    def __init__(self):
        self.subtasks = []
        self.graders = dict()
        self.checker_src = None
        self.checker = None
        self.compiled_checker = None
        self.testcases = []
        self.subtasks = []
        self.generated_testcases = None

    def add_testcase(self, testcase):
        self.testcases.append(testcase)

    def add_subtask(self, subtask):
        if subtask.tc_range[1] >= len(self.testcases):
            raise ValueError("Subtask with unknown testcase given")
        self.subtasks.append(subtask)

    def add_checker(self, checker_src):
        self.checker_src = checker_src

    def add_grader(self, grader_src):
        lang = Language.from_file(grader_src)
        if lang not in self.graders:
            self.graders[lang] = []
        self.graders[lang].append(grader_src)
