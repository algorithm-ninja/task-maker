#!/usr/bin/env python3

from os.path import join, isdir, dirname


def find_task_dir(task_dir: str, max_depth: int):
    if task_dir.endswith("/"):
        task_dir = task_dir[:-1]
    current_format = detect_format(task_dir)
    if current_format or max_depth == 0:
        return task_dir, current_format
    return find_task_dir(dirname(task_dir), max_depth - 1)


def detect_format(task_dir: str):
    ioi = is_ioi_format(task_dir)
    terry = is_terry_format(task_dir)
    if ioi and not terry:
        return "ioi"
    elif terry and not ioi:
        return "terry"
    return None


def is_ioi_format(task_dir: str):
    if isdir(join(task_dir, "gen")) or isdir(join(task_dir, "input")):
        return True
    return False


def is_terry_format(task_dir: str):
    if isdir(join(task_dir, "managers")):
        return True
    return False
