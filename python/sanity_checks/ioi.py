#!/usr/bin/env python3
from distutils.spawn import find_executable
import os.path
import re
import subprocess
import time
from typing import List, Set, Optional, Dict

from task_maker.args import CacheMode
from task_maker.config import Config
from task_maker.formats import Task, list_files, VALIDATION_INPUT_NAME, TaskType
from task_maker.languages import Language
from task_maker.solution import Solution, get_checker_execution
from task_maker.task_maker_frontend import Frontend, File, Execution, Result, \
    ResultStatus
from task_maker.uis.ioi import IOIUIInterface


def _get_languages(solutions: List[Solution]):
    languages = set()
    for solution in solutions:
        languages.add(solution.solution.language)
    return languages


def _has_grader(solutions: List[Solution]):
    return any(sol.solution.grader for sol in solutions)


def _check_graders(folder: str, languages: Set[Language],
                   solutions: List[Solution], interface: IOIUIInterface):
    # if there is at least a grader assume the task is with graders
    if _has_grader(solutions):
        for language in languages:
            if not os.path.exists(folder + "grader" +
                                  language.source_extension):
                interface.add_warning("Missing grader{} in {} folder".format(
                    language.source_extension, folder))


def _get_statement_path():
    for path in ["statement/statement.pdf", "testo/testo.pdf"]:
        if os.path.lexists(path):
            return path
    return None


def _get_statement_tex():
    return list_files(
        ["statement/*.tex", "testo/*.tex"], valid_extensions=[".tex"])


def _check_git_has_file(path: str) -> Optional[bool]:
    # git is not installed
    if not find_executable("git"):
        return None
    proc = subprocess.run(
        ["git", "ls-files", "--", path],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE)
    # this is not a git repository
    if proc.returncode != 0:
        return None
    if proc.stdout.decode():
        return True
    return False


def _check_pdf_statement(interface: IOIUIInterface):
    path = _get_statement_path()
    if not path:
        interface.add_warning("The statement file is missing")
        return
    if _check_git_has_file(path) is False:
        interface.add_warning(
            "The statement file {} is not known to git".format(path))
    if os.path.islink(path):
        realpath = os.path.relpath(path)
        if not os.path.exists(realpath):
            interface.add_warning("The statement is a broken link")


def _check_tex_statement(task: Task, interface: IOIUIInterface):
    statements = _get_statement_tex()
    if not statements:
        return
    regex = r".*\{Subtask ([0-9]+)\} *\[(?:\\phantom\{.\})?([0-9]+).*\].*"
    for statement in statements:
        is_non_sequential = False
        is_wrong = False
        with open(statement, "r") as f:
            matches = re.findall(regex, f.read())
            if not matches:
                continue
            one_based = int(matches[0][0] == '1')
            last = -1
            for subtask, score in matches:
                subtask = int(subtask) - one_based
                score = int(score)
                if subtask != last + 1:
                    is_non_sequential = True
                    # if the numbers are screwed up the scores have no sense
                    break
                last = subtask
                from_task = task.subtasks.get(subtask)
                if not from_task or from_task.max_score != score:
                    is_wrong = True
        if is_non_sequential:
            interface.add_warning(
                "The subtasks in the statement {} are "
                "non-sequentially numbered".format(statement))
        elif is_wrong:
            interface.add_warning(
                "The subtasks in the statement {} don't match "
                "the task's ones".format(statement))


def _setup_execution_callback(interface: IOIUIInterface, execution: Execution,
                              description: str):
    log_prefix = "{} ".format(description).ljust(50)
    interface.printer.text(log_prefix + "WAITING\n")

    def notify_start():
        interface.printer.text(log_prefix + "START\n")
        interface.running[log_prefix] = time.monotonic()

    def get_result(result: Result):
        del interface.running[log_prefix]
        cached = " [cached]" if result.was_cached else ""
        if result.status == ResultStatus.SUCCESS:
            interface.printer.green(log_prefix + "SUCCESS" + cached + "\n")
        else:
            interface.add_error("{} failed".format(description))
            interface.printer.red(
                log_prefix + "FAIL: {} {}\n".format(result.status, cached))

    def skipped():
        interface.printer.red(log_prefix + "SKIPPED\n")

    def get_stderr(stderr):
        if stderr:
            interface.printer.text(log_prefix + "STDERR\n" + stderr + "\n")

    execution.notifyStart(notify_start)
    execution.getResult(get_result, skipped)
    execution.stderr(False).getContentsAsString(get_stderr)


def _setup_checker_callback(interface: IOIUIInterface, checking: Execution,
                            description: str, custom_checker: bool):
    log_prefix = "{} ".format(description).ljust(50)
    interface.printer.text(log_prefix + "WAITING\n")

    def notify_start():
        interface.printer.text(log_prefix + "START\n")
        interface.running[log_prefix] = time.monotonic()

    def get_result(result: Result):
        del interface.running[log_prefix]
        cached = " [cached]" if result.was_cached else ""
        if result.status == ResultStatus.SUCCESS:
            interface.printer.green(log_prefix + "SUCCESS" + cached + "\n")
        else:
            interface.add_error("{} failed".format(description))
            interface.printer.red(
                log_prefix + "FAIL: {} {}\n".format(result.status, cached))

    def skipped():
        interface.printer.red(log_prefix + "SKIPPED\n")

    def get_stdout(stdout):
        if not custom_checker:
            return
        try:
            score = float(stdout)
        except ValueError:
            interface.add_error(description +
                                " failed: invalid score: {}".format(stdout))
            return
        if not 0.0 <= score <= 1.0:
            interface.add_error(description +
                                " failed: invalid score: {}".format(stdout))
            return
        if score == 0.0:
            interface.add_warning(description + " does not score any points")

    checking.notifyStart(notify_start)
    checking.getResult(get_result, skipped)
    checking.stdout(False).getContentsAsString(get_stdout)


def check_att_folder(task: Task, solutions: List[Solution],
                     interface: IOIUIInterface):
    """
    Check if the following files are present:
    - grader.* for all the languages which have a solution
    - task_name.* for all the languages above
    - task_name.inputX.txt / task_name.outputX.txt / inputX.txt / outputX.txt
      making sure that they are symlinks
    """
    languages = _get_languages(solutions)
    _check_graders("att/", languages, solutions, interface)
    if _has_grader(solutions):
        for language in languages:
            if not os.path.exists("att/{}{}".format(
                    task.name, language.source_extension)):
                interface.add_warning("Missing {}{} in att/ folder".format(
                    task.name, language.source_extension))
    sample_files = list_files([
        "att/input*.txt", "att/output*.txt", "att/{}.input*.txt".format(
            task.name), "att/{}.output*.txt".format(task.name)
    ])
    for sample in sample_files:
        if not os.path.islink(sample):
            interface.add_warning(
                "Sample file {} is not a symlink".format(sample))
    if len(sample_files):
        interface.add_warning("No sample files provided")


def check_sol_folder(solutions: List[Solution], interface: IOIUIInterface):
    """
    Check if the following files are present:
    - grader.* for all the languages which have a solution
    - solution.* / soluzione.cpp is a symlink
    """
    languages = _get_languages(solutions)
    _check_graders("sol/", languages, solutions, interface)
    sols = list_files(["sol/solution.*", "sol/soluzione.*"])
    if len(sols) > 1:
        interface.add_warning("More than one official solution found")
    for sol in sols:
        if not os.path.islink(sol):
            interface.add_warning(
                "Official solution {} is not a symlink".format(sol))


def check_statement(task: Task, interface: IOIUIInterface):
    """
    Check if the statement is present and, if git is used, that is known.
    Check that the latex statements, if present contain the same subtasks, with
    the same score, as the task
    Check if the template functions in the statement and in the graders have the
    same signature
    """
    _check_pdf_statement(interface)
    _check_tex_statement(task, interface)
    # TODO check if the template signatures match the one in the statement


def check_sample_cases(task: Task, frontend: Frontend, config: Config,
                       interface: IOIUIInterface):
    """
    Check if the sample cases in the statement are valid and the output is
    correct
    """
    inputs = list_files(
        [
            "statement/input*.txt", "statement/{}.input*.txt".format(
                task.name), "testo/input*.txt", "testo/{}.input*.txt".format(
                    task.name)
        ],
        valid_extensions=[".txt"])
    outputs = list_files(
        [
            "statement/output*.txt", "statement/{}.output*.txt".format(
                task.name), "testo/output*.txt", "testo/{}.output*.txt".format(
                    task.name)
        ],
        valid_extensions=[".txt"])
    num_to_input = dict()  # type: Dict[int, str]
    num_to_output = dict()  # type: Dict[int, str]
    num_to_input_file = dict()  # type: Dict[int, File]
    num_to_output_file = dict()  # type: Dict[int, File]
    num_to_sol_output_file = dict()  # type: Dict[int, File]
    num_to_validation = dict()  # type: Dict[int, File]

    for infile in inputs:
        match = re.match(r".*input(\d+).txt", infile)
        # invalid sample file format, skip it
        if not match:
            continue
        sample_num = int(match.group(1))
        num_to_input[sample_num] = infile
        # skip the validations if there is no default validator
        if not task.default_val:
            break
        num_to_input_file[sample_num] = frontend.provideFile(
            infile, "Sample input {}".format(infile), False)
        validation = task.default_val.source_file.execute(
            frontend, "Validation of sample input {}".format(infile),
            [VALIDATION_INPUT_NAME, "0"])
        if config.cache == CacheMode.NOTHING:
            validation.disableCache()
        validation.addInput(VALIDATION_INPUT_NAME,
                            num_to_input_file[sample_num])
        num_to_validation[sample_num] = validation.stdout(False)
        _setup_execution_callback(
            interface, validation,
            "Validation of sample input {}".format(infile))

    # Communication tasks does not have output files
    if task.task_type != TaskType.Batch:
        return

    for outfile in outputs:
        match = re.match(r".*output(\d+).txt", outfile)
        if not match:
            continue
        sample_num = int(match.group(1))
        # skip the output if there is no corresponding input
        if sample_num not in num_to_input:
            continue
        num_to_output[sample_num] = outfile
        num_to_output_file[sample_num] = frontend.provideFile(
            outfile, "Sample output {}".format(outfile), False)
        # without official solution we cannot solve the input
        if not task.official_solution:
            break
        solving = task.official_solution.execute(
            frontend, "Solving sample output {}".format(outfile), [])
        if config.cache != CacheMode.ALL:
            solving.disableCache()
        solving.addInput("wait_for_validation", num_to_validation[sample_num])
        if task.input_file:
            solving.addInput(task.input_file, num_to_input_file[sample_num])
        else:
            solving.setStdin(num_to_input_file[sample_num])
        if task.output_file:
            num_to_sol_output_file[sample_num] = solving.output(
                task.output_file, False)
        else:
            num_to_sol_output_file[sample_num] = solving.stdout(False)

        _setup_execution_callback(
            interface, solving,
            "Solution of sample input {}".format(num_to_input[sample_num]))

        check = get_checker_execution(
            frontend, config, task, task.checker,
            num_to_input_file[sample_num], num_to_output_file[sample_num],
            num_to_sol_output_file[sample_num],
            "Checking sample output {}".format(outfile))

        _setup_checker_callback(interface, check,
                                "Checking sample output {}".format(outfile),
                                task.checker is not None)


def check_solution_score(task: Task, interface: IOIUIInterface):
    """
    Check if the official solution scores full score
    """
    if not task.official_solution:
        return
    official_solution_name = task.official_solution.name
    if not official_solution_name in interface.testing:
        return
    max_score = sum(st.max_score for st in task.subtasks.values())
    if interface.testing[official_solution_name].score != max_score:
        interface.add_warning(
            "The official solution {} does not score full score".format(
                official_solution_name))


def check_subtask_score_sum(task: Task, interface: IOIUIInterface):
    """
    Check if the sum of the subtask max_score is 100
    """
    if sum(st.max_score for st in task.subtasks.values()) != 100:
        interface.add_warning("The sum of the subtask max scores is not 100")


def sanity_pre_checks(task: Task, solutions: List[Solution],
                      frontend: Frontend, config: Config,
                      interface: IOIUIInterface):
    check_subtask_score_sum(task, interface)
    check_att_folder(task, solutions, interface)
    check_sol_folder(solutions, interface)
    check_statement(task, interface)
    check_sample_cases(task, frontend, config, interface)


def sanity_post_checks(task: Task, solutions: List[Solution],
                       interface: IOIUIInterface):
    check_solution_score(task, interface)
