#!/usr/bin/env python3

import glob
import os
import ruamel.yaml
import shlex
from task_maker.args import UIS, CacheMode, Arch
from task_maker.config import Config
from task_maker.formats import ScoreMode, Subtask, TestCase, IOITask, \
    TaskFormat, list_files, Validator, Generator, get_options, \
    VALIDATION_INPUT_NAME, gen_grader_map, get_write_input_file, \
    get_write_output_file, TaskType, get_solutions
from task_maker.sanitize import sanitize_command
from task_maker.sanity_checks.ioi import sanity_pre_checks, sanity_post_checks
from task_maker.solution import Solution, BatchSolution, CommunicationSolution
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import File, Frontend
from task_maker.uis.ioi import IOIUIInterface, TestcaseGenerationStatus
from task_maker.uis.ioi_curses_ui import IOICursesUI
from task_maker.uis.ioi_finish_ui import IOIFinishUI
from task_maker.uis.ioi_finish_ui_json import IOIFinishUIJSON
from typing import Dict, List, Any, Tuple
from typing import Optional


def load_static_testcases() -> Subtask:
    """
    Generates a subtask with all the static input and output files that match
    input/input*.txt and output/output*.txt. The subtask max_score is 100 and
    the score mode is SUM for historical reasons.
    """
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
    """
    Get the first generator that matches gen/generator.* or gen/generatore.*
    If no generator is found None is returned.
    """
    for generator in list_files(["gen/generator.*", "gen/generatore.*"]):
        return generator
    return None


def get_validator() -> Optional[str]:
    """
    Get the first validator that matches gen/validator.* or gen/valida.*
    If no validator is found None is returned.
    """
    for validator in list_files(["gen/validator.*", "gen/valida.*"]):
        return validator
    return None


def get_official_solution() -> Optional[str]:
    """
    Get the first solution that matches sol/solution.* or sol/soluzione.*
    If no solution is found None is returned.
    """
    for sol in list_files(["sol/solution.*", "sol/soluzione.*"]):
        return sol
    return None


def get_checker() -> Optional[str]:
    """
    Get the first checker that matches check/checker.* or cor/correttore.*
    If no checker is found None is returned.
    """
    checkers = list_files(["check/checker.*", "cor/correttore.*"])
    if not checkers:
        checker = None
    elif len(checkers) == 1:
        checker = checkers[0]
    else:
        raise ValueError("Too many checkers in check/cor folder")
    return checker


def get_manager() -> Optional[str]:
    """
    Get the first manager that matches check/manager.* or cor/manager.*
    If no manager is found None is returned.
    """
    managers = list_files(["check/manager.*", "cor/manager.*"])
    if not managers:
        manager = None
    elif len(managers) == 1:
        manager = managers[0]
    else:
        raise ValueError("Too many managers in check/cor folder")
    return manager


def get_graders(task: IOITask):
    """
    Get the paths of all the graders/stubs according to the task type.
    """
    if task.task_type == TaskType.Communication:
        return list_files(["sol/stub.*"])
    else:
        return list_files(["sol/grader.*"])


def gen_testcases(copy_compiled: bool, task: IOITask) -> Dict[int, Subtask]:
    """
    Compute the list of the subtask of a task by parsing gen/GEN or searching
    the static input/output files. If no subtasks are specified in the gen/GEN
    a single one is created with max_score 100 and ScoreMode SUM for historical
    reasons.
    If the static files are not used a generator, a validator and an official
    solution must be present.
    """
    subtasks = {}  # type: Dict[int, Subtask]

    def create_subtask(subtask_num: int, testcases: Dict[int, TestCase],
                       score: float) -> None:
        if subtask_num < 0:
            return
        if not testcases:
            task.warnings.append("Subtask %d has no subtasks" % subtask_num)
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
        if line.startswith("#ST:"):
            create_subtask(subtask_num, current_testcases, current_score)
            subtask_num += 1
            current_testcases = {}
            current_score = float(line[4:].strip())
            continue
        if line.startswith("#COPY:"):
            testcase = TestCase(None, validator, [], [], line[6:].strip(),
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

    if subtask_num == -1:
        subtask_num = 0
    create_subtask(subtask_num, current_testcases, current_score)
    # Hack for when subtasks are not specified.
    if len(subtasks) == 1 and subtasks[0].max_score == 0:
        subtasks[0].score_mode = ScoreMode.SUM
        subtasks[0].max_score = 100
    return subtasks


def detect_yaml() -> str:
    """
    Search for a task.yaml and returns its path. There are 4 combinations:
    ./task.ya?ml
    ../name_of_the_task.ya?ml
    """
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
    """
    Gets the content of the task.yaml file
    """
    path = detect_yaml()
    with open(path) as yaml_file:
        return ruamel.yaml.safe_load(yaml_file)


def create_task_from_yaml(data: Dict[str, Any]) -> IOITask:
    """
    Extract the base information of the task from the task.yaml file.
    """
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

    task = IOITask(name, title, {}, None, dict(), None, time_limit,
                   memory_limit, input_file if input_file else "",
                   output_file if output_file else "", TaskType.Batch)
    return task


def get_task_without_testcases(config: Config) -> IOITask:
    """
    Compute all the information about the task with the exception of the
    testcases. This function is used also in TM-format but there the inputs
    are generated differently.
    """
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

    graders = get_graders(task)
    task.grader_map = gen_grader_map(graders)

    official_solution = get_official_solution()
    if official_solution is None:
        raise RuntimeError("No official solution found")
    if official_solution:
        task.official_solution = SourceFile.from_file(
            official_solution, task.name, config.copy_exe,
            "bin/official_solution", Arch.DEFAULT, task.grader_map)

    if checker is not None:
        checker_dir = os.path.dirname(checker)
        if checker_dir.endswith("cor"):
            target = os.path.join(checker_dir, "correttore")
        else:
            target = os.path.join(checker_dir, "checker")
        task.checker = SourceFile.from_file(checker, task.name, True, target,
                                            Arch.DEFAULT, {})
    if manager is not None:
        target = os.path.join(os.path.dirname(manager), "manager")
        task.checker = SourceFile.from_file(manager, task.name, True, target,
                                            Arch.DEFAULT, {})
    return task


def get_task(config: Config) -> IOITask:
    """
    Given the Config build all the information about a task.
    """
    task = get_task_without_testcases(config)
    subtasks = gen_testcases(config.copy_exe, task)
    for subtask_num, subtask in subtasks.items():
        task.subtasks[subtask_num] = subtask
    return task


def get_task_solutions(config: Config, task: IOITask) -> List[Solution]:
    """
    Search all the solutions in the sol/ directory (and according to the filters
    specified in the config) prepare and put them in a list.
    """
    data = parse_task_yaml()
    num_processes = get_options(data, ["num_processes"], 1)
    graders = get_graders(task)
    solutions = get_solutions(config.solutions, "sol/", graders)
    sols = []  # type: List[Solution]
    for solution in solutions:
        path, ext = os.path.splitext(os.path.basename(solution))
        source = SourceFile.from_file(solution, task.name, config.copy_exe,
                                      "bin/" + path + "_" + ext[1:],
                                      Arch.DEFAULT, task.grader_map)
        if task.task_type == TaskType.Batch:
            sols.append(BatchSolution(source, task, config, task.checker))
        else:
            sols.append(
                CommunicationSolution(source, task, config, task.checker,
                                      num_processes))

    return sols


def evaluate_task(frontend: Frontend, task: IOITask, solutions: List[Solution],
                  config: Config) -> IOIUIInterface:
    """
    Build the computation DAG and run the evaluation of the task. All the sanity
    checks are also run and a IOIUIInterface with all the results is returned.
    """
    ui_interface = IOIUIInterface(
        task,
        dict((st_num, [tc for tc in st.testcases.keys()])
             for st_num, st in task.subtasks.items()),
        config.ui in [UIS.PRINT, UIS.JSON], config.ui == UIS.JSON)
    curses_ui = None
    finish_ui = None
    if config.ui == UIS.CURSES:
        curses_ui = IOICursesUI(config, ui_interface)
    if config.ui != UIS.SILENT and config.bulk_number is None:
        if config.ui in [UIS.PRINT, UIS.CURSES]:
            finish_ui = IOIFinishUI(config, ui_interface)
        elif config.ui == UIS.JSON:
            finish_ui = IOIFinishUIJSON(config, ui_interface)
        else:
            raise ValueError("Unsupported UI %s" % str(config.ui))

    with ui_interface.run_in_ui(curses_ui, finish_ui):
        ins, outs, vals = generate_inputs(frontend, task, ui_interface, config)
        evaluate_solutions(frontend, ins, outs, vals, solutions, ui_interface,
                           config)

        for warning in task.warnings:
            ui_interface.add_warning(warning)
        sanity_pre_checks(task, solutions, frontend, config, ui_interface)
        frontend.evaluate()
        sanity_post_checks(task, solutions, ui_interface)

    return ui_interface


def generate_inputs(
        frontend, task: IOITask, interface: IOIUIInterface, config: Config
) -> (Dict[Tuple[int, int], File], Dict[Tuple[int, int], File],
      Dict[Tuple[int, int], File]):
    """
    Create the part of the DAG responsible for the input and output files. Will
    return 3 dicts: one for input, one for output and one for validations.
    Each dict has (subtask number, test case number) -> File
    """

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
                try:
                    inputs[testcase_id] = frontend.provideFile(
                        testcase.input_file, "Static input %d" % tc_num, False)

                    if testcase.validator:
                        val = testcase.validator.source_file.execute(
                            frontend, "Validation of input %d" % tc_num,
                            testcase.validator.get_args(
                                testcase, subtask, tc_num, st_num + 1))
                        if config.cache == CacheMode.NOTHING:
                            val.disableCache()
                        val.addInput(VALIDATION_INPUT_NAME,
                                     inputs[testcase_id])
                        validations[testcase_id] = val.stdout(False)

                        interface.add_validation(st_num, tc_num, val)
                except RuntimeError as ex:
                    interface.add_error(str(ex))
                    interface.subtasks[st_num][
                        tc_num].status = TestcaseGenerationStatus.FAILURE
                    continue
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
    """
    Create the evaluation part of the DAG, for each solution at least 2
    executions will be run: the evaluation that produces an output file and
    the checking that produces a score.
    """
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


class IOIFormat(TaskFormat):
    """
    Entry point for the IOI format.
    """

    @staticmethod
    def clean():
        """
        Remove all the generated files, eventually removing also the
        corresponding directory.
        The files removed are: input/output files, bin directory, compiled
        checkers
        """

        def remove_dir(path: str, pattern: str) -> None:
            if not os.path.exists(path):
                return
            for file in glob.glob(os.path.join(path, pattern)):
                os.remove(file)
            try:
                os.rmdir(path)
            except OSError:
                print("Directory %s not empty, kept non-%s files" % (path,
                                                                     pattern))

        def remove_file(path: str) -> None:
            try:
                os.remove(path)
            except OSError:
                pass

        if get_generator():
            remove_dir("input", "*.txt")
            remove_dir("output", "*.txt")
        remove_dir("bin", "*")
        for d in ["cor", "check"]:
            for f in ["checker", "correttore"]:
                remove_file(os.path.join(d, f))

    @staticmethod
    def evaluate_task(frontend: Frontend, config: Config) -> IOIUIInterface:
        """
        Evaluate the task, generating inputs and outputs, compiling all the
        files and checking all the specified solutions.
        """
        task = get_task(config)
        solutions = get_task_solutions(config, task)
        return evaluate_task(frontend, task, solutions, config)
