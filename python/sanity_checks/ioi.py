#!/usr/bin/env python3
import subprocess
from distutils.spawn import find_executable
import os.path
from typing import List, Set, Optional

from task_maker.formats import Task, list_files
from task_maker.languages import Language
from task_maker.solution import Solution
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
        if os.path.exists(path):
            return path
    return None


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


def check_statement(interface: IOIUIInterface):
    """
    Check if the statement is present and, if git is used, that is known.
    Check that the latex statements, if present contain the same subtasks, with
    the same score, as the task
    Check if the template functions in the statement and in the graders have the
    same signature
    """
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
    # TODO check if the subtasks match the one in the statement
    # TODO check if the template signatures match the one in the statement


def check_sample_cases(interface: IOIUIInterface):
    """
    Check if the sample cases in the statement are valid and the output is
    correct
    """
    # TODO run validator on the sample inputs
    # TODO run the solution/checker on the sample outputs


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
                      interface: IOIUIInterface):
    check_subtask_score_sum(task, interface)
    check_att_folder(task, solutions, interface)
    check_sol_folder(solutions, interface)
    check_statement(interface)
    check_sample_cases(interface)


def sanity_post_checks(task: Task, solutions: List[Solution],
                       interface: IOIUIInterface):
    check_solution_score(task, interface)
