#!/usr/bin/env python3
import glob
import json
import os.path
import pprint
from task_maker.args import UIS
from task_maker.config import Config
from task_maker.formats import TaskFormat, Task
from task_maker.formats.terry_format.execution import evaluate_task
from task_maker.formats.terry_format.parsing import get_task, get_task_solutions
from task_maker.task_maker_frontend import Frontend
from typing import List, Tuple


class TerryFormat(TaskFormat):
    """
    Entry point for the terry format
    """

    @staticmethod
    def clean():
        """
        Clean all the generated files: all the compiled managers.
        """

        def remove_file(path: str) -> None:
            try:
                os.remove(path)
            except OSError:
                pass

        for manager in glob.glob("managers/*.*.*"):
            remove_file(manager)

    @staticmethod
    def task_info(config: Config):
        task = get_task(config)
        if config.ui == UIS.JSON:
            print(json.dumps(task.to_dict()))
        elif config.ui != UIS.SILENT:
            pprint.pprint(task.to_dict())

    @staticmethod
    def get_task(config: Config) -> Task:
        return get_task(config)

    @staticmethod
    def evaluate_task(frontend: Frontend, config: Config):
        """
        Evaluate the task, compiling the solutions and testing them.
        """
        task = get_task(config)
        solutions = get_task_solutions(config, task)
        return evaluate_task(frontend, task, solutions, config)

    @staticmethod
    def make_booklet(frontend: Frontend, config: Config,
                     tasks: List[Tuple[str, Task]]) -> int:
        raise NotImplementedError("Terry booklets are not supported yet")
