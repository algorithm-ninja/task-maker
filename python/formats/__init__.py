#!/usr/bin/env python3
import glob
import os.path
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional, Union, Any

from task_maker.config import Config
from task_maker.task_maker_frontend import Frontend
from task_maker.source_file import SourceFile
from task_maker.languages import GraderInfo, LanguageManager, Dependency, \
    Language

VALIDATION_INPUT_NAME = "tm_input_file"


class ScoreMode(Enum):
    MIN = 0
    MAX = 1
    SUM = 2


class TaskType(Enum):
    Batch = 0
    Communication = 1


class Constraint:
    def __init__(self, name: str, lower_bound: Optional[float],
                 upper_bound: Optional[float], more_or_equal: bool,
                 less_or_equal: bool):
        self.name = name
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.more_or_equal = more_or_equal
        self.less_or_equal = less_or_equal

    def accept(self, x: float):
        if self.lower_bound is not None:
            if self.more_or_equal and x < self.lower_bound:
                return False
            if not self.more_or_equal and x <= self.lower_bound:
                return False
        if self.upper_bound is not None:
            if self.less_or_equal and x > self.upper_bound:
                return False
            if not self.less_or_equal and x >= self.upper_bound:
                return False
        return True

    def __str__(self):
        res = ""
        if self.lower_bound is not None:
            res += str(self.lower_bound)
            res += " <= " if self.more_or_equal else " < "
        res += self.name
        if self.upper_bound is not None:
            res += " <= " if self.less_or_equal else " < "
            res += str(self.upper_bound)
        return res

    def __repr__(self):
        return "<Constraint {}>".format(str(self))


class Generator:
    def __init__(self, name: str, source_file: Optional[SourceFile],
                 args_spec: Optional[List[str]]):
        self.name = name
        self.args_spec = args_spec
        self.source_file = source_file

    def __repr__(self):
        return "<Generator %s [%s]>" % (self.name,
                                        " ".join(self.args_spec or []))


class Validator:
    def __init__(self, name: str, source_file: SourceFile,
                 args_spec: Optional[List[str]]):
        self.name = name
        self.source_file = source_file
        self.args_spec = args_spec

    def get_args(self, testcase: "TestCase", subtask: "Subtask", tc_num: int,
                 st_num: int) -> List[str]:
        if not self.args_spec:
            return [VALIDATION_INPUT_NAME, str(st_num)]
        args = []  # type: List[str]
        for arg in self.args_spec:
            if not arg.startswith("$"):
                args.append(arg)
            else:
                args.append(
                    parse_variable(arg, testcase, subtask, tc_num, st_num))
        return args

    def __repr__(self):
        return "<Validator %s [%s]>" % (self.name, " ".join(self.args_spec))


class TestCase:
    def __init__(self, generator: Optional[Generator],
                 validator: Optional[Validator], generator_args: List[str],
                 extra_deps: List[Dependency], input_file: Optional[str],
                 output_file: Optional[str], write_input_to: Optional[str],
                 write_output_to: Optional[str]):
        self.generator = generator
        self.validator = validator
        self.generator_args = generator_args
        self.extra_deps = extra_deps
        self.input_file = input_file
        self.output_file = output_file
        self.write_input_to = write_input_to
        self.write_output_to = write_output_to
        self.matched_params = {}  # type: Dict[str, str]

        if bool(generator) == bool(input_file):
            raise ValueError("Cannot have both generator and static input")

    def __repr__(self):
        return "<TestCase generator=%s args=%s>" % (self.generator,
                                                    str(self.generator_args))


class Subtask:
    def __init__(self, name: str, description: str, score_mode: ScoreMode,
                 max_score: float, testcases: Dict[int, TestCase],
                 constraints: List[Constraint]):
        self.name = name
        self.description = description
        self.constraints = constraints
        self.score_mode = score_mode
        self.max_score = max_score
        self.testcases = testcases

    def __repr__(self):
        return "<Subtask name=%s max_score=%f>" % (self.name, self.max_score)


class Task:
    def __init__(self, name: str, title: str, subtasks: Dict[int, Subtask],
                 official_solution: Optional["SourceFile"],
                 grader_map: Dict[Language, GraderInfo],
                 checker: Optional["SourceFile"], time_limit: float,
                 memory_limit_kb: int, input_file: str, output_file: str,
                 task_type: TaskType):
        self.name = name
        self.title = title
        self.subtasks = subtasks
        self.official_solution = official_solution
        self.grader_map = grader_map
        self.checker = checker
        self.time_limit = time_limit
        self.memory_limit_kb = memory_limit_kb
        self.input_file = input_file
        self.output_file = output_file
        self.task_type = task_type

        self.default_gen = None  # type: Optional[Generator]
        self.default_val = None  # type: Optional[Validator]

    def __repr__(self):
        return "<Task name=%s title=%s>" % (self.name, self.title)


class TerryTask:
    def __init__(self, name: str, title: str, max_score: float):
        self.name = name
        self.title = title
        self.max_score = max_score
        self.generator = None  # type: SourceFile
        self.validator = None  # type: Optional[SourceFile]
        self.official_solution = None  # type: Optional[SourceFile]
        self.checker = None  # type: SourceFile

    def __repr__(self):
        return "<TerryTask name={} title={}>".format(self.name, self.title)


class TaskFormat(ABC):
    @staticmethod
    @abstractmethod
    def evaluate_task(frontend: Frontend, config: Config):
        pass

    @staticmethod
    @abstractmethod
    def clean():
        pass


def get_write_input_file(tc_num: int) -> str:
    return "input/input%d.txt" % tc_num


def get_write_output_file(tc_num: int) -> str:
    return "output/output%d.txt" % tc_num


def get_options(data: Dict[str, Any],
                names: List[str],
                default: Optional[Any] = None) -> Any:
    for name in names:
        if name in data:
            return data[name]
    if not default:
        raise ValueError(
            "Non optional field %s missing from task.yaml" % "|".join(names))
    return default


def list_files(patterns: List[str],
               exclude: Optional[List[str]] = None,
               valid_extensions: List[str] = None) -> List[str]:
    if exclude is None:
        exclude = []
    if valid_extensions is None:
        valid_extensions = LanguageManager.valid_extensions()
    files = [_file for pattern in patterns
             for _file in glob.glob(pattern)]  # type: List[str]
    return [
        res for res in files
        if res not in exclude and os.path.splitext(res)[1] in valid_extensions
    ]


def parse_variable(arg: str, testcase: TestCase, subtask: Subtask, tc_num: int,
                   st_num: int) -> str:
    def format_number(num: Union[int, float]):
        if int(num) == num:
            return str(int(num))
        return str(num)

    cmd = arg[1:]
    if cmd == "ST_NUM":
        return format_number(st_num)
    elif cmd == "ST_NAME":
        return subtask.name
    elif cmd == "TC_NUM":
        return format_number(tc_num)
    elif cmd == "INPUT":
        return VALIDATION_INPUT_NAME
    elif cmd.startswith("MIN_"):
        var = cmd[4:]
        value = None
        for constraint in subtask.constraints:
            if constraint.name == var and \
                    constraint.lower_bound is not None:
                value = max(value or -10**19, constraint.lower_bound)
        if value is None:
            raise ValueError("There are no constraints for the "
                             "minimum of '%s'" % var)
        return format_number(value)
    elif cmd.startswith("MAX_"):
        var = cmd[4:]
        value = None
        for constraint in subtask.constraints:
            if constraint.name == var and \
                    constraint.upper_bound is not None:
                value = min(value or 10**19, constraint.upper_bound)
        if value is None:
            raise ValueError("There are no constraints for the "
                             "maximum of '%s'" % var)
        return format_number(value)
    elif cmd in testcase.matched_params:
        return testcase.matched_params[cmd]
    else:
        raise ValueError(
            "Cannot match variable '%s' in testcase %s" % (arg, testcase))


def gen_grader_map(graders: List[str]):
    grader_map = dict()

    for grader in graders:
        name = os.path.basename(grader)
        language = LanguageManager.from_file(grader)
        info = GraderInfo(
            language,
            [Dependency(name, grader)] + language.get_dependencies(grader))
        grader_map[info.for_language] = info
    return grader_map


def get_solutions(solutions: List[str], directory: str,
                  graders: List[str]) -> List[str]:
    if solutions:
        paths = []
        for sol in solutions:
            if sol.startswith(directory):
                paths.append(sol + "*")
            else:
                paths.append("{}{}*".format(directory, sol))
        solutions = list_files(paths)
    else:
        solutions = list_files(
            [directory + "*"], exclude=graders + [directory + "__init__.py"])
        solutions = list(
            filter(lambda s: not s.startswith(directory + "_"), solutions))
    return solutions
