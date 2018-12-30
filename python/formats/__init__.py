#!/usr/bin/env python3
import glob
import os.path
from abc import ABC, abstractmethod
from enum import Enum
from task_maker.config import Config
from task_maker.languages import GraderInfo, LanguageManager, Dependency, \
    Language
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import Frontend
from typing import List, Dict, Optional, Union, Any, Tuple

# Name of the input file on disk when doing the validation process
VALIDATION_INPUT_NAME = "tm_input_file"


class ScoreMode(Enum):
    """Score mode for a task:
    - MIN: the score is the minimum of all the testcases in the group
    - MAX: same with the maximum
    - SUM: take the sum of the scores, scaled on the task max score
    """
    MIN = 0
    MAX = 1
    SUM = 2


class TaskType(Enum):
    """Type of the task:
    - Batch: a single input file is given to a single solution file that
    produces an output file which is scored by a checker.
    - Communication: a single input file is sent to a manager, this program is
    connected through pipes to the solution executable (which can be spawned
    more than once). They communicate and the manager will score the solution.
    """
    Batch = 0
    Communication = 1


class Constraint:
    """
    Defines a CONSTRAINT in a cases.gen file (TM-format).
    """

    def __init__(self, name: str, lower_bound: Optional[float],
                 upper_bound: Optional[float], more_or_equal: bool,
                 less_or_equal: bool):
        self.name = name
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.more_or_equal = more_or_equal
        self.less_or_equal = less_or_equal

    def accept(self, x: float):
        """
        Checks if `x` is valid according to this constraint
        """
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
    """
    Defines a generator of input files. It's composed by a name that refers to
    a specific SourceFile. Optionally can contain a specification about its
    parameters (the names of them, in order).
    """

    def __init__(self, name: str, source_file: Optional[SourceFile],
                 args_spec: Optional[List[str]]):
        self.name = name
        self.args_spec = args_spec
        self.source_file = source_file

    def __repr__(self):
        return "<Generator %s [%s]>" % (self.name, " ".join(self.args_spec
                                                            or []))


class Validator:
    """
    Defines a validator of testcases. Like Generator it's composed of a name, a
    SourceFile and optionally a list with the names of the parameters
    """

    def __init__(self, name: str, source_file: SourceFile,
                 args_spec: Optional[List[str]]):
        self.name = name
        self.source_file = source_file
        self.args_spec = args_spec

    def get_args(self, testcase: "TestCase", subtask: "Subtask", tc_num: int,
                 st_num: int) -> List[str]:
        """
        Compute the list of arguments to pass to the validator. The parameters
        are used for the variable substitution in case of arguments that start
        with $
        """
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
    """
    Defines a TestCase, specifically all the information about an input/output
    pair. The input file can be obtained from a Generator or using a static
    file. If available a validator is used to check that file. It also stores
    the path of where to write the files to disk.
    Note that a generator and a static file cannot be specified together.
    """

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
    """
    A subtask is a group of test cases. In order to group the score of them a
    ScoreMode is used with a max_score parameter. With TM-format it's also
    possible to specify some constraints for the problem variables.
    """

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


class Task(ABC):
    """
    Abstract class of a Task, each task format should derive from this base
    class.
    """

    def __init__(self, name: str, title: str):
        self.name = name
        self.title = title

        # pre-run time warnings (e.g. parsing warnings)
        self.warnings = []  # type: List[str]


class IOITask(Task):
    """
    IOITask is a format of tasks, usually, but not only, used at IOI. A task has
    some parameters like a time and memory constraint for the contestant
    solutions. The task is composed by testcases grouped in subtasks (eventually
    only one). Every solution _can_ be compiled with a grader, a file specific
    for each supported language.
    The official solution is the one written by the task authors and it will be
    used to generate the output files (if not statically provided).
    The subtasks are 0-based numbered, the testcases as well but their numbers
    wont reset at each subtask. The time limit is expressed in seconds.
    """

    def __init__(self, name: str, title: str, subtasks: Dict[int, Subtask],
                 official_solution: Optional["SourceFile"],
                 grader_map: Dict[Language, GraderInfo],
                 checker: Optional["SourceFile"], time_limit: float,
                 memory_limit_kb: int, input_file: str, output_file: str,
                 task_type: TaskType, yaml: Any):
        super().__init__(name, title)
        self.subtasks = subtasks
        self.official_solution = official_solution
        self.grader_map = grader_map
        self.checker = checker
        self.time_limit = time_limit
        self.memory_limit_kb = memory_limit_kb
        self.input_file = input_file
        self.output_file = output_file
        self.task_type = task_type
        self.yaml = yaml

        self.default_gen = None  # type: Optional[Generator]
        self.default_val = None  # type: Optional[Validator]

    def to_dict(self):
        return {
            "type":
                "IOI",
            "name":
                self.name,
            "title":
                self.title,
            "subtasks": {
                st_num: {
                    "name": subtask.name,
                    "max_score": subtask.max_score,
                    "cases": {
                        tc_num: {
                            "generator":
                                testcase.generator.name
                                if testcase.generator else None,
                            "generator_path":
                                testcase.generator.source_file.path
                                if testcase.generator else None,
                            "args":
                                testcase.generator_args
                        }
                        for tc_num, testcase in subtask.testcases.items()
                    }
                }
                for st_num, subtask in self.subtasks.items()
            },
            "official_solution":
                self.official_solution.name if self.official_solution else None,
            "checker":
                self.checker.name if self.checker else None,
            "time_limit":
                self.time_limit,
            "memory_limit":
                self.memory_limit_kb,
            "input_file":
                self.input_file,
            "output_file":
                self.output_file,
            "task_type":
                self.task_type.name
        }

    def __repr__(self):
        return "<Task name=%s title=%s>" % (self.name, self.title)


class TerryTask(Task):
    """
    TerryTask is a task used in the Terry platform. The system will generate a
    random input, unique for each user, which will be sent to the user's
    solution that produces an output file. There are no time nor memory
    constraints. The output file is then checked and scored by the "checker".
    An official solution can be provided, it will be compiled and put alongside
    the checker.
    """

    def __init__(self, name: str, title: str, max_score: float):
        super().__init__(name, title)
        self.max_score = max_score
        self.generator = None  # type: SourceFile
        self.validator = None  # type: Optional[SourceFile]
        self.official_solution = None  # type: Optional[SourceFile]
        self.checker = None  # type: SourceFile

    def to_dict(self):
        return {
            "type":
                "Terry",
            "name":
                self.name,
            "title":
                self.title,
            "max_score":
                self.max_score,
            "generator":
                self.generator.path if self.generator else None,
            "validator":
                self.validator.path if self.validator else None,
            "official_solution":
                self.official_solution.path if self.official_solution else None,
            "checker":
                self.checker.path if self.checker else None,
        }

    def __repr__(self):
        return "<TerryTask name={} title={}>".format(self.name, self.title)


class TaskFormat(ABC):
    """
    Abstract call that defines the entry points for a task format. Every format
    should derive from this class. The main function will call one of those
    abstract methods to do the action associated to this format.
    """

    @staticmethod
    @abstractmethod
    def evaluate_task(frontend: Frontend, config: Config):
        """
        Given the connection to the Frontend and the Config start the evaluation
        of a task.
        """
        pass

    @staticmethod
    @abstractmethod
    def clean():
        """
        Perform the task cleanup process.
        """
        pass

    @staticmethod
    @abstractmethod
    def task_info(config: Config):
        """
        Print the task information
        """
        pass

    @staticmethod
    @abstractmethod
    def get_task(config: Config) -> Task:
        """
        Build a Task from the config
        """
        pass

    @staticmethod
    @abstractmethod
    def make_booklet(frontend: Frontend, config: Config,
                     tasks: List[Tuple[str, Task]]) -> int:
        """
        Make the booklet of the specified tasks
        """
        pass

    @staticmethod
    @abstractmethod
    def fuzz_checker(config: Config):
        """
        Start fuzzing the checker of the task, if any.
        """
        pass


def get_write_input_file(tc_num: int) -> str:
    """
    Given a test case number produces the path, relative to the task directory,
    of where to write input file.
    """
    return "input/input%d.txt" % tc_num


def get_write_output_file(tc_num: int) -> str:
    """
    Given a test case number produces the path, relative to the task directory,
    of where to write output file.
    """
    return "output/output%d.txt" % tc_num


def get_options(data: Dict[str, Any],
                names: List[str],
                default: Optional[Any] = None) -> Any:
    """
    Given a dict with some string keys, search in it all the keys provided and
    return the value associated with the first item found. If none of the keys
    match the default is returned if specified, otherwise an error is thrown.
    """
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
    """
    List all the files that match the provided patterns, excluding some files
    and filtering only the one with a valid extension. If valid_extensions is
    not provided LanguageManager.valid_extensions() is used.
    """
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
    """
    Parses a command variable name and resolves it. The argument must starts
    with a dollar sign and be followed by a valid variable name:
    - $ST_NUM the number of the subtask
    - $ST_NAME the name of the subtask
    - $TC_NUM the number of the testcase
    - $INPUT the name of the input file (used only in the validation process)
    - $MIN_XXX the minimum valid value of the task variable XXX (must be
    specified by a CONSTRAINT command)
    - $MAX_XXX same as $MIN_XXX but with the maximum value possible.
    - $XXX the value of the generator parameter named XXX for the current
    testcase
    If the variable cannot be replaced or parsed an exception is thrown.
    """

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
                value = max(value or -10 ** 19, constraint.lower_bound)
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
                value = min(value or 10 ** 19, constraint.upper_bound)
        if value is None:
            raise ValueError("There are no constraints for the "
                             "maximum of '%s'" % var)
        return format_number(value)
    elif cmd in testcase.matched_params:
        return testcase.matched_params[cmd]
    else:
        raise ValueError(
            "Cannot match variable '%s' in testcase %s" % (arg, testcase))


def gen_grader_map(graders: List[str]) -> Dict[Language, GraderInfo]:
    """
    Given the list of the paths to the supported grader files computes the
    association between language and grader metadata.
    """
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
    """
    Given some search prefixes (solutions) and a directory where the solutions
    are stored (relative to the task path) returns the list of paths to the
    found solution files:
    - any absolute path to a file
    - only the solution with name starts with one of the specified prefixes and
    are inside the specified directory
    - or the files that matches the prefix specified (even outside directory)
    If no prefix is specified, returns all the solutions that:
    - are inside directory
    - and are not graders
    - and the name does not starts with . (and it's not __init__.py)
    """
    if solutions:
        paths = []
        for sol in solutions:
            if os.path.isabs(sol) and os.path.isfile(sol):
                paths.append(sol)
            elif sol.startswith(directory):
                paths.append(sol + "*")
            else:
                paths.append("{}{}*".format(directory, sol))
        solutions = list_files(paths)
    else:
        solutions = list_files([directory + "*"],
                               exclude=graders + [directory + "__init__.py"])
        solutions = list(
            filter(lambda s: not s.startswith(directory + "."), solutions))
    return solutions
