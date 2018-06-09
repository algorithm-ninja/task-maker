#!/usr/bin/env python3

from os.path import join, isdir, dirname, exists


def find_task_dir(task_dir: str, max_depth: int):
    if task_dir.endswith("/"):
        task_dir = task_dir[:-1]
    current_format = detect_format(task_dir)
    if current_format or max_depth == 0:
        return task_dir, current_format
    return find_task_dir(dirname(task_dir), max_depth - 1)


def detect_format(task_dir: str):
    tm = is_tm_format(task_dir)
    ioi = is_ioi_format(task_dir)
    terry = is_terry_format(task_dir)
    if tm:
        return "tm"
    if ioi and not terry:
        return "ioi"
    elif terry and not ioi:
        return "terry"
    return None


def is_tm_format(task_dir: str):
    return exists(join(task_dir, "gen", "cases.gen"))


def is_ioi_format(task_dir: str):
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
    if isdir(join(task_dir, "managers")):
        return True
    return False
