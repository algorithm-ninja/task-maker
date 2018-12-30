#!/usr/bin/env python3
import glob
import json
import os
import pprint
from task_maker.args import UIS
from task_maker.config import Config
from task_maker.formats import IOITask, TaskFormat, list_files, Task
from task_maker.formats.ioi_format.execution import evaluate_task
from task_maker.formats.ioi_format.fuzz_checker import fuzz_checker
from task_maker.formats.ioi_format.parsing import get_generator, get_task, \
    get_task_solutions
from task_maker.printer import StdoutPrinter, Printer
from task_maker.remote import ExecutionPool
from task_maker.statements.oii_tex import OIITexStatement
from task_maker.task_maker_frontend import Frontend, Result, ResultStatus
from task_maker.uis import UIPrinter
from task_maker.uis.ioi import IOIUIInterface
from typing import Dict, List, Tuple


class IOIFormat(TaskFormat):
    """
    Entry point for the IOI format.
    """

    @staticmethod
    def clean(has_generator=None):
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

        if has_generator or get_generator():
            remove_dir("input", "*.txt")
            remove_dir("output", "*.txt")
        remove_dir("bin", "*")
        for d in ["cor", "check"]:
            for f in ["checker", "correttore"]:
                remove_file(os.path.join(d, f))

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
    def evaluate_task(frontend: Frontend, config: Config) -> IOIUIInterface:
        """
        Evaluate the task, generating inputs and outputs, compiling all the
        files and checking all the specified solutions.
        """
        task = get_task(config)
        solutions = get_task_solutions(config, task)
        return evaluate_task(frontend, task, solutions, config)

    @staticmethod
    def make_booklet(frontend: Frontend, config: Config,
                     tasks: List[Tuple[str, IOITask]]) -> int:
        statements = dict()  # type: Dict[str, List[OIITexStatement]]
        for path, task in tasks:
            config.task_dir = path
            os.chdir(path)
            tex_files = list_files(["statement/*.tex", "testo/*.tex"],
                                   valid_extensions=[".tex"])
            for tex_file in tex_files:
                lang = os.path.basename(tex_file)[:-4]
                statement = OIITexStatement(task, os.path.abspath(tex_file))
                if lang not in statements:
                    statements[lang] = list()
                statements[lang].append(statement)

        if config.ui == UIS.PRINT:
            printer = StdoutPrinter()
        else:
            printer = Printer()
        ui_printer = UIPrinter(printer, config.ui == UIS.JSON)
        pool = ExecutionPool(config, frontend, ui_printer)

        successful_compilations = 0
        for lang, texts in statements.items():
            file_name = "booklet_%s.pdf" % lang
            target_file = os.path.join(config.contest_dir, file_name)
            compilation, pdf_file, deps = OIITexStatement.compile_booklet(
                pool, texts, lang)
            if not pool.config.dry_run:
                pdf_file.getContentsToFile(target_file)

            def on_done(res: Result):
                nonlocal successful_compilations
                if res.status == ResultStatus.SUCCESS or \
                        res.status == ResultStatus.RETURN_CODE:
                    successful_compilations += 1

            compilation.bind(on_done)

        pool.start()
        return len(statements) - successful_compilations

    @staticmethod
    def fuzz_checker(config: Config):
        fuzz_checker(config)
