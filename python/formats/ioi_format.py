#!/usr/bin/env python3

import glob
import os
import shlex
import yaml
from typing import Dict, List, Any, Tuple
from typing import Optional

from task_maker.args import UIS, CacheMode, Arch
from task_maker.config import Config
from task_maker.uis.ioi_finish_ui import IOIFinishUI
from task_maker.uis.ioi_curses_ui import IOICursesUI
from task_maker.uis.ioi import IOIUIInterface
from task_maker.formats import ScoreMode, Subtask, TestCase, Task, \
    list_files, Validator, Generator, get_options, VALIDATION_INPUT_NAME, \
    gen_grader_map, get_write_input_file, get_write_output_file, TaskType, \
    get_solutions
from task_maker.sanitize import sanitize_command
from task_maker.sanity_checks.ioi import sanity_pre_checks, sanity_post_checks
from task_maker.solution import Solution, BatchSolution, CommunicationSolution
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import File, Frontend


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


def gen_testcases(copy_compiled: bool, task: Task) -> Dict[int, Subtask]:
    subtasks = {}  # type: Dict[int, Subtask]

    def create_subtask(subtask_num: int, testcases: Dict[int, TestCase],
                       score: float) -> None:
        if testcases:
            subtask = Subtask("", "", ScoreMode.MIN, score, testcases, [])
            subtasks[subtask_num] = subtask

    generator = get_generator()
    if not generator:
        return {0: load_static_testcases()}
    else:
        gen = SourceFile.from_file(generator, task.name, copy_compiled,
                                   "bin/generator", Arch.DEFAULT, {})
        generator = Generator("default", gen, None)
        task.default_gen = generator
    validator = get_validator()
    if not validator:
        raise RuntimeError("No validator found")
    val = SourceFile.from_file(validator, task.name, copy_compiled,
                               "bin/validator", Arch.DEFAULT, {})
    validator = Validator("default", val, None)
    task.default_val = validator

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
    return subtasks


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
                if output_file else "", TaskType.Batch)
    return task


def get_checker() -> Optional[str]:
    checkers = list_files(["check/checker.*", "cor/correttore.*"])
    if not checkers:
        checker = None
    elif len(checkers) == 1:
        checker = checkers[0]
    else:
        raise ValueError("Too many checkers in check/cor folder")
    return checker


def get_manager() -> Optional[str]:
    managers = list_files(["check/manager.*", "cor/manager.*"])
    if not managers:
        manager = None
    elif len(managers) == 1:
        manager = managers[0]
    else:
        raise ValueError("Too many managers in check/cor folder")
    return manager


def create_task(config: Config):
    copy_compiled = config.copy_exe
    data = parse_task_yaml()
    if not data:
        raise RuntimeError("The task.yaml is not valid")

    task = create_task_from_yaml(data)

    checker = get_checker()
    manager = get_manager()
    if checker and manager:
        raise ValueError("Both checker and manager found")
    if manager:
        task.task_type = TaskType.Communication
    num_processes = get_options(data, ["num_processes"], 1)

    if task.task_type == TaskType.Communication:
        graders = list_files(["sol/stub.*"])
    else:
        graders = list_files(["sol/grader.*"])

    solutions = get_solutions(config.solutions, "sol/", graders)
    grader_map = gen_grader_map(graders, task)

    official_solution = get_official_solution()
    if official_solution is None:
        raise RuntimeError("No official solution found")
    if official_solution:
        task.official_solution = SourceFile.from_file(
            official_solution, task.name, copy_compiled,
            "bin/official_solution", Arch.DEFAULT, grader_map)

    if checker is not None:
        task.checker = SourceFile.from_file(checker, task.name, copy_compiled,
                                            "bin/checker", Arch.DEFAULT, {})
    if manager is not None:
        task.checker = SourceFile.from_file(manager, task.name, copy_compiled,
                                            "bin/manager", Arch.DEFAULT, {})

    sols = []  # type: List[Solution]
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        source = SourceFile.from_file(solution, task.name, copy_compiled,
                                      "bin/" + path + "_" + ext[1:],
                                      Arch.DEFAULT, grader_map)
        if task.task_type == TaskType.Batch:
            sols.append(BatchSolution(source, task, config, task.checker))
        else:
            sols.append(
                CommunicationSolution(source, task, config, task.checker,
                                      num_processes))

    return task, sols


def get_request(config: Config) -> (Task, List[Solution]):
    task, sols = create_task(config)
    subtasks = gen_testcases(config.copy_exe, task)
    for subtask_num, subtask in subtasks.items():
        task.subtasks[subtask_num] = subtask
    return task, sols


def evaluate_task(frontend: Frontend, task: Task, solutions: List[Solution],
                  config: Config):
    ui_interface = IOIUIInterface(
        task,
        dict((st_num, [tc for tc in st.testcases.keys()])
             for st_num, st in task.subtasks.items()), config.ui == UIS.PRINT)
    if config.ui == UIS.CURSES:
        curses_ui = IOICursesUI(ui_interface)
        curses_ui.start()

    ins, outs, vals = generate_inputs(frontend, task, ui_interface, config)
    evaluate_solutions(frontend, ins, outs, vals, solutions, ui_interface,
                       config)

    sanity_pre_checks(task, solutions, frontend, config, ui_interface)
    frontend.evaluate()
    sanity_post_checks(task, solutions, ui_interface)

    if config.ui == UIS.CURSES:
        curses_ui.stop()

    if config.ui != UIS.SILENT:
        finish_ui = IOIFinishUI(config, task, ui_interface)
        finish_ui.print()
    return ui_interface


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

            if task.task_type == TaskType.Batch:
                # static output file
                if testcase.output_file:
                    outputs[testcase_id] = frontend.provideFile(
                        testcase.output_file, "Static output %d" % tc_num,
                        False)
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
                        outputs[testcase_id] = sol.output(
                            task.output_file, False)
                    else:
                        outputs[testcase_id] = sol.stdout(False)

                    interface.add_solving(st_num, tc_num, sol)

                if testcase.write_output_to and not config.dry_run:
                    outputs[testcase_id].getContentsToFile(
                        testcase.write_output_to, True, True)
    if task.checker:
        add_non_solution(task.checker)
    return inputs, outputs, validations


def evaluate_solutions(frontend, inputs: Dict[Tuple[int, int], File],
                       outputs: Dict[Tuple[int, int], File],
                       validations: Dict[Tuple[int, int], File],
                       solutions: List[Solution], interface: IOIUIInterface,
                       config: Config):
    for solution in solutions:
        solution.solution.prepare(frontend, config)
        interface.add_solution(solution.solution)
        for testcase_id, input in inputs.items():
            st_num, tc_num = testcase_id
            evals, check = solution.evaluate(frontend, tc_num, st_num,
                                             inputs[testcase_id],
                                             validations.get(testcase_id),
                                             outputs.get(testcase_id))
            interface.add_evaluate_solution(st_num, tc_num,
                                            solution.solution.name, evals)
            interface.add_evaluate_checking(st_num, tc_num,
                                            solution.solution.name, check)


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
