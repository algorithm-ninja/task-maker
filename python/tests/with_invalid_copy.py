#!/usr/bin/env python3

from task_maker.tests.test import run_tests


def test_task():
    from task_maker.tests.utils import TestInterface
    interface = TestInterface("with_invalid_copy", "Testing task-maker", 1, 65536)
    interface.set_errors("Read where/am/i.txt: No such file or directory")
    interface.run_checks()


if __name__ == "__main__":
    run_tests("with_invalid_copy", __file__)
