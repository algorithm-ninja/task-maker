#!/usr/bin/env python3
import argparse
from typing import List, IO
from typing import Optional

from manager_pb2 import EvaluateTaskRequest
from task_maker.formats.ioi_format import list_files, parse_task_yaml, \
    create_task_from_yaml, get_solutions, get_checker


class TMConstraint:
    def __init__(self, name: str, lower_bound: Optional[float],
                 upper_bound: Optional[float], more_or_equal: bool,
                 less_or_equal: bool):
        self.name = name
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.more_or_equal = more_or_equal
        self.less_or_equal = less_or_equal

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
        return "<Generator %s (%s [%s])>" %\
               (self.name, self.path, " ".join(self.args))


class TMValidator:
    def __init__(self, name: str, path: str, args: Optional[List[str]]):
        self.name = name
        self.path = path
        self.args = args

    def __repr__(self):
        return "<Validator %s (%s [%s])>" % \
               (self.name, self.path, " ".join(self.args))


class TMTestcase:
    def __init__(self, args: List[str], generator: TMGenerator,
                 validator: TMValidator):
        self.args = args
        self.generator = generator
        self.validator = validator


class TMSubtask:
    def __init__(self, max_score: float, name: str, score_mode: int):
        self.max_score = max_score
        self.name = name
        self.score_mode = score_mode
        self.constraints = []  # type: List[TMConstraint]
        self.testcases = []  # type: List[TMTestcase]


def parse_cases(gen: IO) -> List[TMSubtask]:
    lines = [l.strip() for l in gen.readlines()]

    subtasks = []  # type: List[TMSubtask]
    generators = []  # type: List[TMGenerator]
    validators = []  # type: List[TMValidator]
    constraints = []  # type: List[TMConstraint]
    current_gen = None  # type: Optional[TMGenerator]
    current_val = None  # type: Optional[TMValidator]

    def parse_command(line: str):
        return filter(bool, line[1:].strip().split(" "))

    def process_GEN(args):
        # global GEN definitions
        if not subtasks:
            if len(args) < 2:
                raise ValueError("The GEN command needs al least 2 arguments: "
                                 "name path [args [args ...]] (line %d)" %
                                 (lineno))
            generators.append(TMGenerator(args[0], args[1], args[2:]))
        # subtask local GEN
        else:
            raise NotImplementedError()

    def process_VAL(args):
        # global VAL definitions
        if not subtasks:
            if len(args) < 2:
                raise ValueError("The VAL command needs al least 2 arguments: "
                                 "name path [args [args ...]] (line %d)" %
                                 (lineno))
            validators.append(TMValidator(args[0], args[1], args[2:]))
        # subtask local VAL
        else:
            raise NotImplementedError()

    def process_CONSTRAINT(args):
        # there are 3 main cases:
        # a) L < X
        # b) X < U
        # c) L < X < U

        constraint = TMConstraint("X", 0, 1, False, True)
        # global constraints
        if not subtasks:
            constraints.append(constraint)
        # subtask constraints
        else:
            raise NotImplementedError()

    for lineno, line in enumerate(lines):
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
            else:
                raise ValueError("Unknown command '%s' in '%s' (line %d)" %
                                 (cmd, line, lineno))
        # a simple testcase
        else:
            pass


def get_request(args: argparse.Namespace) -> EvaluateTaskRequest:
    copy_compiled = args.copy_exe
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)
    graders = list_files(["sol/grader.*"])
    solutions = get_solutions(args.solutions, graders)
    checker = get_checker()
    with open("gen/cases.gen", "r") as gen:
        subtasks = parse_cases(gen)
