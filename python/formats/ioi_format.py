#!/usr/bin/env python3

import glob
import os
import shlex
import yaml
from typing import Dict, List, Any, Tuple
from typing import Optional

from task_maker.args import UIS, CacheMode
from task_maker.config import Config
from task_maker.uis.ioi_finish_ui import IOIFinishUI
from task_maker.uis.ioi_curses_ui import IOICursesUI
from task_maker.uis.ioi import IOIUIInterface
from task_maker.formats import ScoreMode, Subtask, TestCase, Task, \
    list_files, Validator, Generator, get_options, VALIDATION_INPUT_NAME, \
    gen_grader_map, get_write_input_file, get_write_output_file
from task_maker.sanitize import sanitize_command
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import File, Frontend, Resources


def load_static_testcases() -> Subtask:
    nums = [
        int(input_file[11:-4])
        for input_file in glob.glob(os.path.join("input", "input*.txt"))
    ]
    if not nums:
        raise RuntimeError("No generator and no input files found!")

    subtask = Subtask("Static testcases",
                      "Testcases imported without a generator", ScoreMode.SUM,
                      100, {}, [])

    for num in sorted(nums):
        testcase = TestCase(None, None, [], [],
                            os.path.join("input", "input%d.txt" % num),
                            os.path.join("output", "output%d.txt" % num),
                            get_write_input_file(num),
                            get_write_output_file(num))
        subtask.testcases[num] = testcase
    return subtask


def get_generator() -> Optional[str]:
    for generator in list_files(["gen/generator.*", "gen/generatore.*"]):
        return generator
    return None


def get_validator() -> Optional[str]:
    for validator in list_files(["gen/validator.*", "gen/valida.*"]):
        return validator
    return None


def get_official_solution() -> Optional[str]:
    for sol in list_files(["sol/solution.*", "sol/soluzione.*"]):
        return sol
    return None


def gen_testcases(
        copy_compiled: bool) -> Tuple[Optional[str], Dict[int, Subtask]]:
    subtasks = {}  # type: Dict[int, Subtask]

    def create_subtask(subtask_num: int, testcases: Dict[int, TestCase],
                       score: float) -> None:
        if testcases:
            subtask = Subtask("Subtask {}".format(subtask_num), "",
                              ScoreMode.MIN, score, testcases, [])
            subtasks[subtask_num] = subtask

    generator = get_generator()
    if not generator:
        return None, {0: load_static_testcases()}
    else:
        generator = Generator(
            "default",
            SourceFile.from_file(generator, copy_compiled and "bin/generator"),
            None)
    validator = get_validator()
    if not validator:
        raise RuntimeError("No validator found")
    validator = Validator(
        "default",
        SourceFile.from_file(validator, copy_compiled and "bin/validator"),
        None)

    official_solution = get_official_solution()
    if official_solution is None:
        raise RuntimeError("No official solution found")

    current_testcases = {}  # type: Dict[int, TestCase]
    subtask_num = -1  # the first #ST line will skip a subtask!
    testcase_num = 0
    current_score = 0.0
    for line in open("gen/GEN"):
        if line.startswith("#ST: "):
            create_subtask(subtask_num, current_testcases, current_score)
            subtask_num += 1
            current_testcases = {}
            current_score = float(line.strip()[5:])
            continue
        if line.startswith("#COPY: "):
            testcase = TestCase(None, validator, [], [], line[7:].strip(),
                                None, get_write_input_file(testcase_num),
                                get_write_output_file(testcase_num))
        else:
            line = line.split("#")[0].strip()
            if not line:
                continue
            # a new testcase without subtask
            if subtask_num < 0:
                subtask_num = 0
            args = shlex.split(line)
            arg_deps = sanitize_command(args)
            testcase = TestCase(generator, validator, args, arg_deps, None,
                                None, get_write_input_file(testcase_num),
                                get_write_output_file(testcase_num))
        current_testcases[testcase_num] = testcase
        testcase_num += 1

    create_subtask(subtask_num, current_testcases, current_score)
    # Hack for when subtasks are not specified.
    if len(subtasks) == 1 and subtasks[0].max_score == 0:
        subtasks[0].score_mode = ScoreMode.SUM
        subtasks[0].max_score = 100
    return official_solution, subtasks


def detect_yaml() -> str:
    cwd = os.getcwd()
    task_name = os.path.basename(cwd)
    yaml_names = ["task", os.path.join("..", task_name)]
    yaml_ext = ["yaml", "yml"]
    for name in yaml_names:
        for ext in yaml_ext:
            path = os.path.join(cwd, name + "." + ext)
            if os.path.exists(path):
                return path
    raise FileNotFoundError("Cannot find the task yaml of %s" % cwd)


def parse_task_yaml() -> Dict[str, Any]:
    path = detect_yaml()
    with open(path) as yaml_file:
        return yaml.load(yaml_file)


def create_task_from_yaml(data: Dict[str, Any]) -> Task:
    name = get_options(data, ["name", "nome_breve"])
    title = get_options(data, ["title", "nome"])
    if name is None:
        raise ValueError("The name is not set in the yaml")
    if title is None:
        raise ValueError("The title is not set in the yaml")

    time_limit = get_options(data, ["time_limit", "timeout"])
    memory_limit = get_options(data, ["memory_limit", "memlimit"]) * 1024
    input_file = get_options(data, ["infile"], "input.txt")
    output_file = get_options(data, ["outfile"], "output.txt")

    task = Task(name, title, {}, None, [], None, time_limit, memory_limit,
                input_file if input_file else "", output_file
                if output_file else "")
    return task


def get_solutions(solutions, graders) -> List[str]:
    if solutions:
        solutions = list_files([
            sol + "*" if sol.startswith("sol/") else "sol/" + sol + "*"
            for sol in solutions
        ])
    else:
        solutions = list_files(
            ["sol/*"], exclude=graders + ["sol/__init__.py"])
    return solutions


def get_checker() -> Optional[str]:
    checkers = list_files(["cor/checker.*", "cor/correttore.cpp"])
    if not checkers:
        checker = None
    elif len(checkers) == 1:
        checker = checkers[0]
    else:
        raise ValueError("Too many checkers in cor/ folder")
    return checker


def get_request(config: Config) -> (Task, List[SourceFile]):
    copy_compiled = config.copy_exe
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)

    graders = list_files(["sol/grader.*"])
    solutions = get_solutions(config.solutions, graders)
    checker = get_checker()

    grader_map = gen_grader_map(graders, task)

    official_solution, subtasks = gen_testcases(copy_compiled)
    if official_solution:
        task.official_solution = SourceFile.from_file(
            official_solution,
            copy_compiled and "bin/official_solution",
            grader_map=grader_map)

    if checker is not None:
        task.checker = SourceFile.from_file(checker, copy_compiled
                                            and "bin/checker")
    for subtask_num, subtask in subtasks.items():
        task.subtasks[subtask_num] = subtask

    sols = []  # type: List[SourceFile]
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        bin_file = copy_compiled and "bin/" + path + "_" + ext[1:]
        sols.extend(
            [SourceFile.from_file(solution, bin_file, grader_map=grader_map)])

    return task, sols


def evaluate_task(frontend: Frontend, task: Task, solutions: List[SourceFile],
                  config: Config):
    ui_interface = IOIUIInterface(
        task,
        dict((st_num, [tc for tc in st.testcases.keys()])
             for st_num, st in task.subtasks.items()), config.ui == UIS.PRINT)
    if config.ui == UIS.CURSES:
        curses_ui = IOICursesUI(ui_interface)
        curses_ui.start()

    ins, outs, vals = generate_inputs(frontend, task, ui_interface, config)
    evaluate_solutions(frontend, task, ins, outs, vals, solutions,
                       ui_interface, config)

    frontend.evaluate()
    if config.ui == UIS.CURSES:
        curses_ui.stop()

    if config.ui != UIS.SILENT:
        finish_ui = IOIFinishUI(task, ui_interface)
        finish_ui.print()


def generate_inputs(frontend, task: Task, interface: IOIUIInterface,
                    config: Config) -> (Dict[Tuple[int, int], File], Dict[
                        Tuple[int, int], File], Dict[Tuple[int, int], File]):
    def add_non_solution(source: SourceFile):
        if not source.prepared:
            source.prepare(frontend, config)
            interface.add_non_solution(source)

    inputs = dict()  # type: Dict[Tuple[int, int], File]
    outputs = dict()  # type: Dict[Tuple[int, int], File]
    validations = dict()  # type: Dict[Tuple[int, int], File]
    for st_num, subtask in task.subtasks.items():
        for tc_num, testcase in subtask.testcases.items():
            testcase_id = (st_num, tc_num)

            if testcase.validator:
                add_non_solution(testcase.validator.source_file)

            # static input file
            if testcase.input_file:
                inputs[testcase_id] = frontend.provideFile(
                    testcase.input_file, "Static input %d" % tc_num, False)
                if testcase.validator:
                    val = testcase.validator.source_file.execute(
                        frontend, "Validation of input %d" % tc_num,
                        testcase.validator.get_args(testcase, subtask, tc_num,
                                                    st_num + 1))
                    if config.cache == CacheMode.NOTHING:
                        val.disableCache()
                    val.addInput(VALIDATION_INPUT_NAME, inputs[testcase_id])
                    validations[testcase_id] = val.stdout(False)

                    interface.add_validation(st_num, tc_num, val)
            # generate input file
            else:
                add_non_solution(testcase.generator.source_file)

                gen = testcase.generator.source_file.execute(
                    frontend, "Generation of input %d" % tc_num,
                    testcase.generator_args)
                for dep in testcase.extra_deps:
                    gen.addInput(
                        dep.name,
                        frontend.provideFile(dep.path, dep.path, False))
                if config.cache == CacheMode.NOTHING:
                    gen.disableCache()
                inputs[testcase_id] = gen.stdout(False)

                interface.add_generation(st_num, tc_num, gen)

                val = testcase.validator.source_file.execute(
                    frontend, "Validation of input %d" % tc_num,
                    testcase.validator.get_args(testcase, subtask, tc_num,
                                                st_num + 1))
                if config.cache == CacheMode.NOTHING:
                    val.disableCache()
                val.addInput(VALIDATION_INPUT_NAME, inputs[testcase_id])
                validations[testcase_id] = val.stdout(False)

                interface.add_validation(st_num, tc_num, val)

            if testcase.write_input_to and not config.dry_run:
                inputs[testcase_id].getContentsToFile(testcase.write_input_to,
                                                      True, True)

            # static output file
            if testcase.output_file:
                outputs[testcase_id] = frontend.provideFile(
                    testcase.output_file, "Static output %d" % tc_num, False)
            else:
                add_non_solution(task.official_solution)

                sol = task.official_solution.execute(
                    frontend, "Generation of output %d" % tc_num, [])
                if config.cache == CacheMode.NOTHING:
                    sol.disableCache()
                if testcase_id in validations:
                    sol.addInput("wait_for_validation",
                                 validations[testcase_id])
                if task.input_file:
                    sol.addInput(task.input_file, inputs[testcase_id])
                else:
                    sol.setStdin(inputs[testcase_id])
                if task.output_file:
                    outputs[testcase_id] = sol.output(task.output_file, False)
                else:
                    outputs[testcase_id] = sol.stdout(False)

                interface.add_solving(st_num, tc_num, sol)

            if testcase.write_output_to and not config.dry_run:
                outputs[testcase_id].getContentsToFile(
                    testcase.write_output_to, True, True)
    return inputs, outputs, validations


def evaluate_solutions(
        frontend, task: Task, inputs: Dict[Tuple[int, int], File],
        outputs: Dict[Tuple[int, int], File],
        validations: Dict[Tuple[int, int], File], solutions: List[SourceFile],
        interface: IOIUIInterface, config: Config):
    def add_non_solution(source: SourceFile):
        if not source.prepared:
            source.prepare(frontend, config)
            interface.add_non_solution(source)

    for solution in solutions:
        solution.prepare(frontend, config)
        interface.add_solution(solution)
        for testcase_id, input in inputs.items():
            st_num, tc_num = testcase_id
            eval = solution.execute(
                frontend,
                "Evaluation of %s on testcase %d" % (solution.name, tc_num),
                [])
            if config.cache != CacheMode.ALL:
                eval.disableCache()
            limits = Resources()
            limits.cpu_time = task.time_limit
            limits.wall_time = task.time_limit * 1.5
            limits.memory = task.memory_limit_kb
            eval.setLimits(limits)
            if testcase_id in validations:
                eval.addInput("tm_wait_validation", validations[testcase_id])
            if task.input_file:
                eval.addInput(task.input_file, inputs[testcase_id])
            else:
                eval.setStdin(inputs[testcase_id])
            if task.output_file:
                output = eval.output(task.output_file, False)
            else:
                output = eval.stdout(False)
            if config.exclusive:
                eval.makeExclusive()

            interface.add_evaluate_solution(st_num, tc_num, solution.name,
                                            eval)

            if task.checker:
                add_non_solution(task.checker)
                check = task.checker.execute(
                    frontend,
                    "Checking solution %s for testcase %d" % testcase_id,
                    ["input", "output", "contestant_output"])
                check.addInput("input", inputs[testcase_id])
            else:
                check = frontend.addExecution(
                    "Checking solution %s for testcase %d" % (solution.name,
                                                              tc_num))
                check.setExecutablePath("diff")
                check.setArgs(["-w", "output", "contestant_output"])
            check.addInput("output", outputs[testcase_id])
            check.addInput("contestant_output", output)
            if config.cache != CacheMode.ALL:
                check.disableCache()
            limits = Resources()
            limits.cpu_time = task.time_limit * 2
            limits.wall_time = task.time_limit * 1.5 * 2
            limits.memory = task.memory_limit_kb * 2
            check.setLimits(limits)
            interface.add_evaluate_checking(st_num, tc_num, solution.name,
                                            check)


def clean():
    def remove_dir(path: str, pattern: str) -> None:
        if not os.path.exists(path):
            return
        for file in glob.glob(os.path.join(path, pattern)):
            os.remove(file)
        try:
            os.rmdir(path)
        except OSError:
            print(
                "Directory %s not empty, kept non-%s files" % (path, pattern))

    def remove_file(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    if get_generator():
        remove_dir("input", "*.txt")
        remove_dir("output", "*.txt")
    remove_dir("bin", "*")
    remove_file(os.path.join("cor", "checker"))
    remove_file(os.path.join("cor", "correttore"))
