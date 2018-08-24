#!/usr/bin/env python3
import argparse
import os.path
from task_maker.config import Config
from typing import List, IO, Dict, Union
from typing import Optional
import shlex

from task_maker.dependency_finder import find_dependency
from task_maker.formats import ioi_format, Task, GraderInfo, Dependency
from task_maker.formats.ioi_format import list_files, parse_task_yaml, \
    create_task_from_yaml, get_solutions, get_checker, get_generator, \
    get_validator, get_official_solution, VALIDATION_INPUT_NAME, gen_grader_map
from task_maker.language import grader_from_file
from task_maker.sanitize import sanitize_command
from task_maker.source_file import SourceFile


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
                raise ValueError(
                    "The GEN command needs al least 2 arguments: "
                    "name path [args [args ...]] (line %d)" % (lineno))
            name = args[0]
            if name in generators:
                raise ValueError(
                    "Duplicate GEN definition at line %d" % lineno)
            generator = TMGenerator(name, args[1], args[2:])
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

    def process_VAL(args):
        nonlocal default_val, current_val
        # global VAL definitions
        if not subtasks:
            if len(args) < 2:
                raise ValueError(
                    "The VAL command needs al least 2 arguments: "
                    "name path [args [args ...]] (line %d)" % (lineno))
            name = args[0]
            if name in validators:
                raise ValueError(
                    "Duplicate VAL definition at line %d" % lineno)
            validator = TMValidator(name, args[1], args[2:])
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
                raise ValueError(
                    "CONSTRAINT is always false (line %d)" % lineno)
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
            raise ValueError(
                "Invalid format for CONSTRAINT (line %d)" % lineno)

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
            raise ValueError(
                "Invalid SUBTASK score '%s' (line %d)" % (args[0], lineno))
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
            raise ValueError(
                "Cannot DESCRIPTION without subtasks (line %d)" % lineno)
        if not args:
            raise ValueError("No description provided (line %s)" % lineno)
        desc = " ".join(args)
        subtasks[-1].description = desc

    def process_COPY(args):
        if not subtasks:
            raise ValueError("Cannot COPY without subtasks (line %d)" % lineno)
        if len(args) != 1:
            raise ValueError(
                "Invalid number of arguments to COPY (line %d)" % lineno)
        if not current_val:
            raise ValueError("No VAL available (line %d)" % lineno)
        testcase = TMTestcase([args[0]], TMCopyGenerator(), current_val)
        testcase.val_args = testcase.validator.get_args(
            testcase, subtasks[-1], tc_num, st_num)
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
                                         "(line %d)" % (constraint, name,
                                                        float(value), lineno))
        testcase.val_args = validator.get_args(testcase, subtasks[-1], tc_num,
                                               st_num)
        subtasks[-1].testcases.append(testcase)
        tc_num += 1

    def process_RUN(args):
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


def generate_gen_GEN(subtasks: List[TMSubtask]):
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
        for testcase in subtask.testcases:
            if isinstance(testcase.generator, TMCopyGenerator):
                GEN += "#COPY: %s\n" % testcase.gen_args[0]
            else:
                # TODO add a custom wrapper to make this works with cmsMake
                GEN += "%s %s\n" % (testcase.generator.path, " ".join(
                    testcase.gen_args))
    return GEN


def get_request(config: Config) -> (Task, List[SourceFile]):
    copy_compiled = config.copy_exe
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)

    graders = list_files(["sol/grader.*"])
    solutions = get_solutions(config.solutions, graders)
    checker = get_checker()
    if checker is not None:
        task.checker = SourceFile.from_file(checker, copy_compiled
                                            and "bin/checker")

    grader_map = gen_grader_map(graders, task)

    official_solution = get_official_solution()
    if official_solution is None:
        raise RuntimeError("No official solution found")
    task.official_solution = SourceFile.from_file(
        official_solution,
        copy_compiled and "bin/official_solution",
        grader_map=grader_map)

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

                tc.generator.CopyFrom(
                    from_file(generator.path, copy_compiled
                              and "bin/generator"))
                tc.generator_args.extend(testcase.gen_args)
                tc.extra_deps.extend(arg_deps)
                tc.validator.CopyFrom(
                    from_file(validator.path, copy_compiled
                              and "bin/validator"))
                tc.validator_args.extend(testcase.val_args)
            st.testcases[testcase_num].CopyFrom(tc)
            testcase_num += 1
        task.subtasks[st_num].CopyFrom(st)

    for grader in graders:
        info = GraderInfo()
        info.for_language = grader_from_file(grader)
        name = os.path.basename(grader)
        info.files.extend([Dependency(name=name, path=grader)] +
                          find_dependency(grader))
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
