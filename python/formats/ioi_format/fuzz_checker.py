#!/usr/bin/env python3
import json
import os.path
import random
import shutil
from task_maker.config import Config
from task_maker.manager import get_frontend
from task_maker.printer import Printer
from task_maker.remote import ExecutionPool, Execution
from task_maker.task_maker_frontend import Result, ResultStatus
from task_maker.uis import UIPrinter
from task_maker.utils import result_to_dict

BATCH_SIZE = 100


class FuzzCheckerState:
    def __init__(self):
        self.batch_num = 0
        self.num_tests = 0
        self.num_successes = 0
        self.num_fails = 0

    def __str__(self):
        return "Batch %3d | %4d tests | %d failed (%.2f%%)" % (
            self.batch_num, self.num_tests, self.num_fails,
            100 * self.num_fails / self.num_tests)

    def bind(self, results_dir: str, generator: Execution, checker: Execution):
        def gen_on_done(res: Result):
            if res.status != ResultStatus.SUCCESS:
                raise RuntimeError("radamsa failed! %s %s" %
                                   (generator.name, result_to_dict(res)))
            self.num_tests += 1

        def check_on_done(res: Result):
            failed = False
            out = checker.stdout_content_bytes
            score = -1
            try:
                score = float(out.decode())
            except:
                failed = True
            if not 0.0 <= score <= 1.0:
                failed = True
            if res.status != ResultStatus.SUCCESS:
                failed = True

            if not failed:
                self.num_successes += 1
                return

            self.num_fails += 1
            dest_dir = os.path.join(results_dir, "fail%d" % self.num_fails)
            os.makedirs(dest_dir, exist_ok=True)
            with open(os.path.join(dest_dir, "fuzz_output"), "wb") as f:
                f.write(generator.stdout_content_bytes)
            with open(os.path.join(dest_dir, "checker_stdout"), "wb") as f:
                f.write(checker.stdout_content_bytes)
            with open(os.path.join(dest_dir, "checker_stderr"), "wb") as f:
                f.write(checker.stderr_content_bytes)
            with open(os.path.join(dest_dir, "data.json"), "w") as f:
                data = {
                    "data": checker.ui_print_data,
                    "result": result_to_dict(checker.result)
                }
                f.write(json.dumps(data, indent=4))

        generator.bind(gen_on_done)
        checker.bind(check_on_done)


def fuzz_checker(config: Config):
    in_file, out_file = config.fuzz_checker
    if not os.path.exists(in_file):
        raise ValueError("The input file does not exists")
    if not os.path.exists(out_file):
        raise ValueError("The output file does not exists")

    from task_maker.formats.ioi_format import get_task
    task = get_task(config)
    if not task.checker:
        raise ValueError("This task does not have a checker")

    results_dir = os.path.join(config.cwd, "fuzz_checker_" + task.name)
    os.makedirs(results_dir, exist_ok=True)
    shutil.copy(in_file, os.path.join(results_dir, "input.txt"))
    shutil.copy(out_file, os.path.join(results_dir, "output.txt"))

    ui_printer = UIPrinter(Printer(), False)
    state = FuzzCheckerState()
    while True:
        state.batch_num += 1
        frontend = get_frontend(config)
        pool = ExecutionPool(config, frontend, ui_printer)

        input = frontend.provideFile(in_file, "Input file")
        output = frontend.provideFile(out_file, "Output file")
        task.checker.unprepare()
        task.checker.prepare(pool)

        for num in range(BATCH_SIZE):
            seed = random.randint(0, 10 ** 9)
            gen = Execution(
                "Generation of output %d of batch %d" % (num, state.batch_num),
                pool,
                "radamsa", ["--seed", str(seed), "-"],
                "fuzz-checker-radamsa",
                ui_print_data={
                    "batch": state.batch_num,
                    "num": num,
                    "seed": seed
                },
                cache_on=[],
                stdin=output,
                store_stdout_bytes=True)
            fuzz_output = gen.stdout
            check = Execution(
                "Checking output %d of batch %d" % (num, state.batch_num),
                pool,
                task.checker, ["input", "output", "fuzz"],
                "fuzz-checker-checker",
                ui_print_data={
                    "batch": state.batch_num,
                    "num": num,
                    "seed": seed
                },
                cache_on=[],
                inputs={
                    "input": input,
                    "output": output,
                    "fuzz": fuzz_output
                },
                store_stdout_bytes=True,
                store_stderr_bytes=True)
            state.bind(results_dir, gen, check)

        def compilation_on_done(res: Result):
            if res.status != ResultStatus.SUCCESS:
                print("Failed to compile the checker")
                print(task.checker.compilation.stderr_content)
                pool.stop()

        if task.checker.compilation:
            task.checker.compilation.bind(compilation_on_done)

        pool.start()
        print(state)
        if pool.stopped:
            return state.num_fails
