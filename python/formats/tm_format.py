#!/usr/bin/env python3
import os.path
import shlex
from typing import List, IO, Dict
from typing import Optional

from task_maker.args import Arch
from task_maker.config import Config
from task_maker.formats import ioi_format, Task, \
    Subtask, Generator, Validator, Constraint, ScoreMode, TestCase, \
    parse_variable, get_write_input_file, \
    get_write_output_file
from task_maker.formats.ioi_format import get_generator, \
    get_validator, create_task
from task_maker.source_file import SourceFile


def parse_cases(gen: IO, task: Task, copy_compiled: bool) -> List[Subtask]:
    lines = [l.strip() for l in gen.readlines()]

    subtasks = []  # type: List[Subtask]
    generators = dict()  # type: Dict[str, Generator]
    validators = dict()  # type: Dict[str, Validator]
    constraints = []  # type: List[Constraint]
    current_gen = None  # type: Optional[Generator]
    current_val = None  # type: Optional[Validator]
    default_gen = None  # type: Optional[Generator]
    default_val = None  # type: Optional[Validator]
    tc_num = 0
    st_num = -1  # will be incremented at the first : SUBTASK
    guessed_gen = get_generator()
    if guessed_gen:
        default_gen = Generator(
            "default",
            SourceFile.from_file(guessed_gen, task.name, copy_compiled,
                                 "bin/gen_default", Arch.DEFAULT, {}), [])
    guessed_val = get_validator()
    if guessed_val:
        default_val = Validator(
            "default",
            SourceFile.from_file(guessed_val, task.name, copy_compiled,
                                 "bin/val_default", Arch.DEFAULT, {}), [])

    def is_float(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def parse_command(line: str):
        return shlex.split(line[1:])

    def process_GEN(args: List[str]):
        nonlocal default_gen, current_gen
        # global GEN definitions
        if not subtasks:
            if len(args) < 2:
                raise ValueError(
                    "The GEN command needs al least 2 arguments: "
                    "name path [args [args ...]] (line %d)" % lineno)
            name = args[0]
            if name in generators:
                raise ValueError(
                    "Duplicate GEN definition at line %d" % lineno)
            generator = Generator(
                name,
                SourceFile.from_file(args[1], task.name, copy_compiled,
                                     "bin/gen_" + name, Arch.DEFAULT, {}),
                args[2:])
            generators[name] = generator
            if name == "default":
                default_gen = generator
        # subtask local GEN
        else:
            if len(args) != 1:
                raise ValueError(
                    "The GEN command for overriding the generator "
                    "needs only one parameter (line %d)" % lineno)
            name = args[0]
            if name not in generators:
                raise ValueError(
                    "Generator '%s' not declared (line %d)" % lineno)
            current_gen = generators[name]

    def process_VAL(args: List[str]):
        nonlocal default_val, current_val
        # global VAL definitions
        if not subtasks:
            if len(args) < 2:
                raise ValueError(
                    "The VAL command needs al least 2 arguments: "
                    "name path [args [args ...]] (line %d)" % lineno)
            name = args[0]
            if name in validators:
                raise ValueError(
                    "Duplicate VAL definition at line %d" % lineno)
            validator = Validator(
                name,
                SourceFile.from_file(args[1], task.name, copy_compiled,
                                     "bin/val_" + name, Arch.DEFAULT, {}),
                args[2:])
            validators[name] = validator
            if name == "default":
                default_val = validator
        # subtask local VAL
        else:
            if len(args) != 1:
                raise ValueError(
                    "The VAL command for overriding the validator "
                    "needs only one parameter (line %d)" % lineno)
            name = args[0]
            if name not in validators:
                raise ValueError(
                    "Validator '%s' not declared (line %d)" % lineno)
            current_val = validators[name]

    def process_CONSTRAINT(args: List[str]):
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
            raise ValueError(
                "Invalid operator passed to CONSTRAINT (line %d)" % lineno)
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
            constraint = Constraint(var, float(args[0]), None, more_or_equal,
                                    False)
        # case b
        elif len(args) == 3 and is_float(args[2]) and args[1][0] == "<":
            if args[0][0] != "$":
                raise ValueError("Expecting variable name in CONSTRAINT "
                                 "(line %d)" % lineno)
            var = args[0][1:]
            constraint = Constraint(var, None, float(args[2]), False,
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
                raise ValueError(
                    "CONSTRAINT is always false (line %d)" % lineno)
            constraint = Constraint(var, float(args[0]), float(args[4]),
                                    more_or_equal, less_or_equal)
        # case d
        elif len(args) == 3 and is_float(args[2]) and args[1][0] == ">":
            if args[0][0] != "$":
                raise ValueError("Expecting variable name in CONSTRAINT "
                                 "(line %d)" % lineno)
            var = args[0][1:]
            constraint = Constraint(var, float(args[2]), None, more_or_equal,
                                    False)
        else:
            raise ValueError(
                "Invalid format for CONSTRAINT (line %d)" % lineno)

        # global constraints
        if not subtasks:
            constraints.append(constraint)
        # subtask constraints
        else:
            subtasks[-1].constraints.append(constraint)

    def process_SUBTASK(args: List[str]):
        nonlocal current_gen, current_val, st_num
        if len(args) < 1:
            raise ValueError("Invalid arguments to SUBTASK: max_score [name] "
                             "(line %d)" % lineno)
        if not is_float(args[0]):
            raise ValueError(
                "Invalid SUBTASK score '%s' (line %d)" % (args[0], lineno))
        st_num += 1
        name = " ".join(args[1:])
        subtask = Subtask(name, "", ScoreMode.MIN, float(args[0]), {},
                          constraints.copy())
        subtasks.append(subtask)
        current_gen = default_gen
        current_val = default_val

    def process_DESCRIPTION(args: List[str]):
        if not subtasks:
            raise ValueError(
                "Cannot DESCRIPTION without subtasks (line %d)" % lineno)
        if not args:
            raise ValueError("No description provided (line %s)" % lineno)
        desc = " ".join(args)
        subtasks[-1].description = desc

    def process_COPY(args: List[str]):
        nonlocal tc_num
        if not subtasks:
            raise ValueError("Cannot COPY without subtasks (line %d)" % lineno)
        if len(args) != 1:
            raise ValueError(
                "Invalid number of arguments to COPY (line %d)" % lineno)
        if not current_val:
            raise ValueError("No VAL available (line %d)" % lineno)
        testcase = TestCase(None, current_val, [], [], args[0], None,
                            get_write_input_file(tc_num),
                            get_write_output_file(tc_num))
        subtasks[-1].testcases[tc_num] = testcase
        tc_num += 1

    def add_testcase(args: List[str], generator: Generator,
                     validator: Validator):
        nonlocal tc_num
        testcase = TestCase(generator, validator, args, [], None, None,
                            get_write_input_file(tc_num),
                            get_write_output_file(tc_num))
        if generator.args_spec:
            if len(generator.args_spec) != len(args):
                raise ValueError("Number of params mismatch the definition "
                                 "(line %d)" % lineno)
            for index, (name, value) in enumerate(
                    zip(generator.args_spec, args)):
                if value.startswith("$"):
                    value = parse_variable(value, testcase, subtasks[-1],
                                           tc_num, st_num)
                    testcase.generator_args[index] = value
                testcase.matched_params[name] = value
                for constraint in subtasks[-1].constraints:
                    if name != constraint.name or not is_float(value):
                        continue
                    if not constraint.accept(float(value)):
                        raise ValueError("Constraint not met: %s when %s=%f "
                                         "(line %d)" % (constraint, name,
                                                        float(value), lineno))
        subtasks[-1].testcases[tc_num] = testcase
        tc_num += 1

    def process_RUN(args: List[str]):
        if not subtasks:
            raise ValueError("Cannot RUN without subtasks (line %d)" % lineno)
        if len(args) < 1:
            raise ValueError(
                "RUN needs al least an argument (line %d)" % lineno)
        name = args[0]
        if name not in generators:
            raise ValueError("Generator '%s' not declared (line %d)" % lineno)
        add_testcase(args[1:], generators[name], current_val)

    def process_TESTCASE(args):
        if not subtasks:
            raise ValueError(
                "Cannot add a testcase  without subtasks (line %d)" % lineno)
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


def generate_gen_GEN(subtasks: List[Subtask]):
    GEN = "# Generated by task-maker. Do not edit!\n"
    GEN += "# tm-allow-delete\n"

    for subtask in subtasks:
        GEN += "\n#ST: %d\n" % int(subtask.max_score)
        name = ""
        if subtask.name:
            name += " " + subtask.name
        if subtask.description:
            name += " " + subtask.description
        if name:
            GEN += "#%s\n" % name
        for constraint in subtask.constraints:
            GEN += "# %s\n" % str(constraint)
        for testcase in subtask.testcases.values():
            if testcase.generator:
                # TODO add a custom wrapper to make this works with cmsMake
                GEN += "%s %s\n" % (testcase.generator.name, " ".join(
                    [shlex.quote(a) for a in testcase.generator_args]))
            else:
                GEN += "#COPY: %s\n" % testcase.input_file
    return GEN


def get_request(config: Config) -> (Task, List[SourceFile]):
    task, sols = create_task(config)
    with open("gen/cases.gen", "r") as gen:
        subtasks = parse_cases(gen, task, config.copy_exe)

    for st_num, subtask in enumerate(subtasks):
        task.subtasks[st_num] = subtask

    if config.dry_run:
        return task, sols
    if os.path.exists("gen/GEN"):
        with open("gen/GEN") as f:
            if "tm-allow-delete" not in f.read(1024):
                return task, sols

    with open("gen/GEN", "w") as f:
        f.write(generate_gen_GEN(subtasks))
    return task, sols


def clean():
    ioi_format.clean()
    if os.path.exists("gen/GEN"):
        with open("gen/GEN") as f:
            if "tm-allow-delete" not in f.read():
                print("Kept non task-maker gen/GEN")
            else:
                os.remove("gen/GEN")
