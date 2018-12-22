#!/usr/bin/env python3

from os.path import join, isdir, dirname, exists
from task_maker.args import TaskFormat
from typing import Tuple, Optional


def find_task_dir(task_dir: str, max_depth: int,
                  hint: TaskFormat) -> Tuple[str, Optional[TaskFormat]]:
    """
    Find the root directory of the task which should be a parent folder of
    task_dir. It must be at most max_depth directories above the current one.
    """
    if task_dir.endswith("/"):
        task_dir = task_dir[:-1]
    current_format = detect_format(task_dir, hint)
    if current_format or max_depth == 0:
        return task_dir, current_format
    return find_task_dir(dirname(task_dir), max_depth - 1, hint)


def detect_format(task_dir: str, hint: TaskFormat) -> Optional[TaskFormat]:
    """
    Detect the format of the task in task_dir, using hint if it matches the
    format of the task.
    """
    valid_formats = []
    if is_tm_format(task_dir):
        valid_formats.append(TaskFormat.TM)
    if is_ioi_format(task_dir):
        valid_formats.append(TaskFormat.IOI)
    if is_terry_format(task_dir):
        valid_formats.append(TaskFormat.TERRY)
    if hint and valid_formats:
        if hint in valid_formats:
            return hint
        else:
            raise ValueError(
                "Non compatible task format {}, valid formats are {}".format(
                    hint, [f.name for f in valid_formats]))
    if valid_formats:
        return valid_formats[0]
    return None


def is_tm_format(task_dir: str) -> bool:
    """
    Check if the format could be task-maker
    """
    return exists(join(task_dir, "gen", "cases.gen"))


def is_ioi_format(task_dir: str):
    """
    Check if the format could be IOI-like
    """
    if isdir(join(task_dir, "gen")):
        if exists(join(task_dir, "gen", "GEN")) and \
                not exists(join(task_dir, "gen", "cases.gen")):
            return True
        else:
            return False
    if isdir(join(task_dir, "input")):
        return True
    return False


def is_terry_format(task_dir: str):
    """
    Check if the format could be Terry-like
    """
    if isdir(join(task_dir, "managers")):
        return True
    return False
