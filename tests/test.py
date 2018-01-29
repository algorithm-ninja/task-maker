#!/usr/bin/env python3
import os.path
import shutil
import sys
from typing import List

import _pytest.config  # type:ignore

from python.args import UIS
from python.silent_ui import SilentUI
from python.task_maker import main


class TestingUI(SilentUI):
    inst = None

    def __init__(self, solutions: List[str]) -> None:
        super().__init__(solutions)
        TestingUI.inst = self

    def fatal_error(self, msg: str) -> None:
        print("FATAL ERROR", msg, file=sys.stderr)


# inject the testing UI to the valid UIs
UIS["testing"] = TestingUI


def run_tests(task_name, file):
    task_dir = "task_" + task_name
    orig_task_dir = os.path.join(os.path.dirname(__file__), task_dir)
    task_path = os.path.join(os.getenv("TEST_TMPDIR", "/tmp"), task_dir)
    if os.path.exists(task_path):
        shutil.rmtree(task_path)
    shutil.copytree(orig_task_dir, task_path)

    os.chdir(task_path)

    sys.argv = [
        sys.argv[0], "--ui=testing", "--cache=nothing",
        "--task-dir=" + task_path, "--dry-run"
    ]

    main()
    raise SystemExit(
        _pytest.config.main(
            [file, "--override-ini=python_classes=IDontWantThis"]))

