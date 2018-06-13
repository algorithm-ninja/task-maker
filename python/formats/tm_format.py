#!/usr/bin/env python3
import argparse
import os.path
from typing import List, IO, Dict, Union
from typing import Optional
import shlex

from manager_pb2 import EvaluateTaskRequest
from task_maker.absolutize import absolutize_request
from task_maker.dependency_finder import find_dependency
from task_maker.formats import ioi_format
from task_maker.formats.ioi_format import list_files, parse_task_yaml, \
    create_task_from_yaml, get_solutions, get_checker, get_generator, \
    get_validator, get_official_solution, VALIDATION_INPUT_NAME
from task_maker.language import grader_from_file
from task_maker.sanitize import sanitize_command
from task_maker.source_file import from_file
from task_pb2 import Subtask, MIN, TestCase, GraderInfo, Dependency


class TMConstraint:
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

    def __repr__(self):
        res = "<Constraint "
        if self.lower_bound is not None:
            res += str(self.lower_bound)
            res += " <= " if self.more_or_equal else " < "
        res += self.name
        if self.upper_bound is not None:
            res += " <= " if self.less_or_equal else " < "
            res += str(self.upper_bound)
        res += ">"
        return res


class TMGenerator:
    def __init__(self, name: str, path: str, args: Optional[List[str]]):
        self.name = name
        self.path = path
        self.args = args

    def __repr__(self):
        return "<Generator %s (%s [%s])>" % \
               (self.name, self.path, " ".join(self.args))


class TMCopyGenerator(TMGenerator):
    def __init__(self):
        super().__init__("COPY", "", None)

    def __repr__(self):
        return "<CopyGenerator>"


class TMValidator:
    def __init__(self, name: str, path: str, args: Optional[List[str]]):
        self.name = name
        self.path = path
        self.args = args

    def get_args(self, testcase: "TMTestcase", subtask: "TMSubtask",
                 tc_num: int, st_num: int) -> List[str]:
        if not self.args:
            return [VALIDATION_INPUT_NAME, str(st_num)]
        args = []  # type: List[str]
        for arg in self.args:
            if not arg.startswith("$"):
                args.append(arg)
            else:
                args.append(parse_variable(arg, testcase, subtask, tc_num,
                                           st_num))
        return args

    def __repr__(self):
        return "<Validator %s (%s [%s])>" % \
               (self.name, self.path, " ".join(self.args))


class TMTestcase:
    def __init__(self, gen_args: List[str], generator: TMGenerator,
                 validator: TMValidator):
        self.gen_args = gen_args
        self.val_args = []  # type: List[str]
        self.generator = generator
        self.validator = validator
        self.matched_params = {}  # type: Dict[str, str]

    def __repr__(self):
        return "<Testcase %s %s | val=%s>" % \
               (self.generator.name, " ".join(self.gen_args),
                self.validator.name)


class TMSubtask:
    def __init__(self, max_score: float, name: str):
        self.max_score = max_score
        self.name = name
        self.description = None  # type: Optional[str]
        self.constraints = []  # type: List[TMConstraint]
        self.testcases = []  # type: List[TMTestcase]

    def __repr__(self):
        return "<Subtask score=%f name=%s desc='%s' %d testcases " \
               "%d constraints>" % \
               (self.max_score, self.name, str(self.description),
                len(self.testcases), len(self.constraints))


def parse_variable(arg: str, testcase: "TMTestcase", subtask: "TMSubtask",
                   tc_num: int, st_num: int) -> str:
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
                value = max(value or -10 ** 18, constraint.lower_bound)
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
                value = min(value or 10 ** 18, constraint.upper_bound)
        if value is None:
            raise ValueError("There are no constraints for the "
                             "maximum of '%s'" % var)
        return format_number(value)
    elif cmd in testcase.matched_params:
        return testcase.matched_params[cmd]
    else:
        raise ValueError("Cannot match variable '%s' in testcase %s" %
                         (arg, testcase))


def parse_cases(gen: IO) -> List[TMSubtask]:
    lines = [l.strip() for l in gen.readlines()]

    subtasks = []  # type: List[TMSubtask]
    generators = dict()  # type: Dict[str, TMGenerator]
    validators = dict()  # type: Dict[str, TMValidator]
    constraints = []  # type: List[TMConstraint]
    current_gen = None  # type: Optional[TMGenerator]
    current_val = None  # type: Optional[TMValidator]
    default_gen = None  # type: Optional[TMGenerator]
    default_val = None  # type: Optional[TMValidator]
    tc_num = 0
    st_num = -1  # will be incremented at the first : SUBTASK
    guessed_gen = get_generator()
    if guessed_gen:
        default_gen = TMGenerator("default", guessed_gen, [])
    guessed_val = get_validator()
    if guessed_val:
        default_val = TMValidator("default", guessed_val, [])

    def is_float(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def parse_command(line: str):
        return shlex.split(line[1:])

    def process_GEN(args):
        nonlocal default_gen, current_gen
        # global GEN definitions
        if not subtasks:
            if len(args) < 2:
                raise ValueError("The GEN command needs al least 2 arguments: "
                                 "name path [args [args ...]] (line %d)" %
                                 (lineno))
            name = args[0]
            if name in generators:
                raise ValueError("Duplicate GEN definition at line %d" % lineno)
            generator = TMGenerator(name, args[1], args[2:])
            generators[name] = generator
            if name == "default":
                default_gen = generator
        # subtask local GEN
        else:
            if len(args) != 1:
                raise ValueError("The GEN command for overriding the generator "
                                 "needs only one parameter (line %d)" % lineno)
            name = args[0]
            if name not in generators:
                raise ValueError("Generator '%s' not declared (line %d)" %
                                 lineno)
            current_gen = generators[name]

    def process_VAL(args):
        nonlocal default_val, current_val
        # global VAL definitions
        if not subtasks:
            if len(args) < 2:
                raise ValueError("The VAL command needs al least 2 arguments: "
                                 "name path [args [args ...]] (line %d)" %
                                 (lineno))
            name = args[0]
            if name in validators:
                raise ValueError("Duplicate VAL definition at line %d" % lineno)
            validator = TMValidator(name, args[1], args[2:])
            validators[name] = validator
            if name == "default":
                default_val = validator
        # subtask local VAL
        else:
            if len(args) != 1:
                raise ValueError("The VAL command for overriding the validator "
                                 "needs only one parameter (line %d)" % lineno)
            name = args[0]
            if name not in validators:
                raise ValueError("Validator '%s' not declared (line %d)" %
                                 lineno)
            current_val = validators[name]

    def process_CONSTRAINT(args):
        # there are 4 cases:
        # a) 42   < $XXX
        # b) $XXX < 123
        # c) 42   < $XXX < 123
        # d) $XXX > 42

        if len(args) not in [3, 5]:
            raise ValueError("Invalid number of arguments passed to "
                             "CONSTRAINT (line %d)" % lineno)
        if args[1] not in ["<", "<=", ">", ">="] or \
                (len(args) == 5 and args[3] not in ["<", "<="]):
            raise ValueError("Invalid operator passed to CONSTRAINT (line %d)" %
                             lineno)
        if args[1][0] == "<":
            more_or_equal = args[1] == "<="
        else:
            more_or_equal = args[1] == ">="
        less_or_equal = args[3] == "<=" if len(args) == 5 else False

        # case a
        if len(args) == 3 and is_float(args[0]):
            if args[2][0] != "$":
                raise ValueError("Expecting variable name in CONSTRAINT "
                                 "(line %d)" % lineno)
            var = args[2][1:]
            constraint = TMConstraint(var, float(args[0]), None, more_or_equal,
                                      False)
        # case b
        elif len(args) == 3 and is_float(args[2]) and args[1][0] == "<":
            if args[0][0] != "$":
                raise ValueError("Expecting variable name in CONSTRAINT "
                                 "(line %d)" % lineno)
            var = args[0][1:]
            constraint = TMConstraint(var, None, float(args[2]), False,
                                      more_or_equal)
        # case c
        elif len(args) == 5 and is_float(args[0]) and is_float(args[4]):
            if args[2][0] != "$":
                raise ValueError("Expecting variable name in CONSTRAINT "
                                 "(line %d)" % lineno)
            lowest_ok = float(args[0]) if more_or_equal else float(args[0]) + 1
            hiest_ok = float(args[4]) if less_or_equal else float(args[4]) - 1
            var = args[2][1:]
            if lowest_ok > hiest_ok:
                raise ValueError("CONSTRAINT is always false (line %d)" %
                                 lineno)
            constraint = TMConstraint(var, float(args[0]), float(args[4]),
                                      more_or_equal, less_or_equal)
        # case d
        elif len(args) == 3 and is_float(args[2]) and args[1][0] == ">":
            if args[0][0] != "$":
                raise ValueError("Expecting variable name in CONSTRAINT "
                                 "(line %d)" % lineno)
            var = args[0][1:]
            constraint = TMConstraint(var, float(args[2]), None, more_or_equal,
                                      False)
        else:
            raise ValueError("Invalid format for CONSTRAINT (line %d)" % lineno)

        # global constraints
        if not subtasks:
            constraints.append(constraint)
        # subtask constraints
        else:
            subtasks[-1].constraints.append(constraint)

    def process_SUBTASK(args):
        nonlocal current_gen, current_val, st_num
        if len(args) < 1 or len(args) > 2:
            raise ValueError("Invalid arguments to SUBTASK: max_score [name] "
                             "(line %d)" % lineno)
        if not is_float(args[0]):
            raise ValueError("Invalid SUBTASK score '%s' (line %d)" %
                             (args[0], lineno))
        st_num += 1
        name = " ".join(args[1:])
        subtask = TMSubtask(float(args[0]), name)
        for constraint in constraints:
            subtask.constraints.append(constraint)
        subtasks.append(subtask)
        current_gen = default_gen
        current_val = default_val

    def process_DESCRIPTION(args):
        if not subtasks:
            raise ValueError("Cannot DESCRIPTION without subtasks (line %d)" %
                             lineno)
        if not args:
            raise ValueError("No description provided (line %s)" % lineno)
        desc = " ".join(args)
        subtasks[-1].description = desc

    def process_COPY(args):
        if not subtasks:
            raise ValueError("Cannot COPY without subtasks (line %d)" % lineno)
        if len(args) != 1:
            raise ValueError("Invalid number of arguments to COPY (line %d)"
                             % lineno)
        if not current_val:
            raise ValueError("No VAL available (line %d)" % lineno)
        testcase = TMTestcase([args[0]], TMCopyGenerator(), current_val)
        testcase.val_args = testcase.validator.get_args(testcase, subtasks[-1],
                                                        tc_num, st_num)
        subtasks[-1].testcases.append(testcase)

    def add_testcase(args: List[str], generator: TMGenerator,
                     validator: TMValidator):
        nonlocal tc_num
        testcase = TMTestcase(args, generator, validator)
        if generator.args:
            if len(generator.args) != len(args):
                raise ValueError("Number of params mismatch the definition "
                                 "(line %d)" % lineno)
            for index, (name, value) in enumerate(zip(generator.args, args)):
                if value.startswith("$"):
                    value = parse_variable(value, testcase, subtasks[-1],
                                           tc_num, st_num)
                    testcase.gen_args[index] = value
                testcase.matched_params[name] = value
                for constraint in subtasks[-1].constraints:
                    if name != constraint.name or not is_float(value):
                        continue
                    if not constraint.accept(float(value)):
                        raise ValueError("Constraint not met: %s when %s=%f "
                                         "(line %d)" %
                                         (constraint, name, float(value),
                                          lineno))
        testcase.val_args = validator.get_args(testcase, subtasks[-1], tc_num,
                                               st_num)
        subtasks[-1].testcases.append(testcase)
        tc_num += 1

    def process_RUN(args):
        if not subtasks:
            raise ValueError("Cannot RUN without subtasks (line %d)" % lineno)
        if len(args) < 1:
            raise ValueError("RUN needs al least an argument (line %d)" %
                             lineno)
        name = args[0]
        if name not in generators:
            raise ValueError("Generator '%s' not declared (line %d)" % lineno)
        add_testcase(args[1:], generators[name], current_val)

    def process_TESTCASE(args):
        if not subtasks:
            raise ValueError("Cannot add a testcase  without subtasks (line %d)"
                             % lineno)
        if not current_gen:
            raise ValueError("No GEN available (line %d)" % lineno)
        if not current_val:
            raise ValueError("No VAL available (line %d)" % lineno)
        add_testcase(args, current_gen, current_val)

    for lineno, line in enumerate(lines, 1):
        # skip empty lines
        if not line:
            continue
        # skip the comments
        if line.startswith("#"):
            continue
        # a command
        if line.startswith(":"):
            cmd, *args = parse_command(line)
            if cmd == "GEN":
                process_GEN(args)
            elif cmd == "VAL":
                process_VAL(args)
            elif cmd == "CONSTRAINT":
                process_CONSTRAINT(args)
            elif cmd == "SUBTASK":
                process_SUBTASK(args)
            elif cmd == "DESCRIPTION":
                process_DESCRIPTION(args)
            elif cmd == "COPY":
                process_COPY(args)
            elif cmd == "RUN":
                process_RUN(args)
            else:
                raise ValueError("Unknown command '%s' in '%s' (line %d)" %
                                 (cmd, line, lineno))
        # a simple testcase
        else:
            process_TESTCASE(shlex.split(line))
    return subtasks


def generate_gen_GEN(subtasks: List[TMSubtask]):
    GEN = "# Generated by task-maker. Do not edit!\n"
    GEN += "# tm-allow-delete\n"

    for subtask in subtasks:
        GEN += "\n#ST: %f\n" % int(subtask.max_score)
        name = ""
        if subtask.name:
            name += " " + subtask.name
        if subtask.description:
            name += " " + subtask.description
        if name:
            GEN += "#%s\n" % name
        for constraint in subtask.constraints:
            GEN += "# %s\n" % str(constraint)
        for testcase in subtask.testcases:
            if isinstance(testcase.generator, TMCopyGenerator):
                GEN += "#COPY: %s\n" % testcase.gen_args[0]
            else:
                # TODO add a custom wrapper to make this works with cmsMake
                GEN += "%s %s\n" % (testcase.generator.path, " ".join(testcase.gen_args))
    return GEN


def get_request(args: argparse.Namespace) -> EvaluateTaskRequest:
    copy_compiled = args.copy_exe
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)
    graders = list_files(["sol/grader.*"])
    solutions = get_solutions(args.solutions, graders)
    checker = get_checker()
    if checker is not None:
        task.checker.CopyFrom(from_file(checker,
                                        copy_compiled and "bin/checker"))
    official_solution = get_official_solution()
    if official_solution is None:
        raise RuntimeError("No official solution found")
    task.official_solution.CopyFrom(
        from_file(official_solution, copy_compiled
                  and "bin/official_solution"))
    with open("gen/cases.gen", "r") as gen:
        subtasks = parse_cases(gen)

    testcase_num = 0
    for st_num, subtask in enumerate(subtasks):
        st = Subtask()
        st.score_mode = MIN
        st.max_score = subtask.max_score
        for testcase in subtask.testcases:
            tc = TestCase()
            if isinstance(testcase.generator, TMCopyGenerator):
                tc.input_file = testcase.gen_args[0]
            else:
                generator = testcase.generator
                validator = testcase.validator
                arg_deps = sanitize_command(testcase.gen_args)

                tc.generator.CopyFrom(from_file(generator.path, copy_compiled
                                                and "bin/generator"))
                tc.generator_args.extend(testcase.gen_args)
                tc.extra_deps.extend(arg_deps)
                tc.validator.CopyFrom(from_file(validator.path, copy_compiled
                                                and "bin/validator"))
                tc.validator_args.extend(testcase.val_args)
            st.testcases[testcase_num].CopyFrom(tc)
            testcase_num += 1
        task.subtasks[st_num].CopyFrom(st)

    for grader in graders:
        info = GraderInfo()
        info.for_language = grader_from_file(grader)
        name = os.path.basename(grader)
        info.files.extend(
            [Dependency(name=name, path=grader)] + find_dependency(grader))
        task.grader_info.extend([info])

    request = EvaluateTaskRequest()
    request.task.CopyFrom(task)
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        bin_file = copy_compiled and "bin/" + path + "_" + ext[1:]
        request.solutions.extend([from_file(solution, bin_file)])
    request.store_dir = args.store_dir
    request.temp_dir = args.temp_dir
    request.exclusive = args.exclusive
    request.extra_time = args.extra_time
    request.keep_sandbox = args.keep_sandbox
    for testcase in range(testcase_num):
        request.write_inputs_to[testcase] = "input/input%d.txt" % testcase
        request.write_outputs_to[testcase] = "output/output%d.txt" % testcase
    request.write_checker_to = "cor/checker"
    request.cache_mode = args.cache.value
    if args.num_cores:
        request.num_cores = args.num_cores
    request.dry_run = args.dry_run
    if args.evaluate_on:
        request.evaluate_on = args.evaluate_on
    absolutize_request(request)
    if os.path.exists("gen/GEN"):
        with open("gen/GEN") as f:
            if "tm-allow-delete" not in f.read():
                return request
    with open("gen/GEN", "w") as f:
        f.write(generate_gen_GEN(subtasks))
    return request


def clean():
    ioi_format.clean()
    if os.path.exists("gen/GEN"):
        with open("gen/GEN") as f:
            if "tm-allow-delete" not in f.read():
                print("Kept non task-maker gen/GEN")
        os.remove("gen/GEN")
