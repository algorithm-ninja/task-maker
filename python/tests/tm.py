#!/usr/bin/env python3

from task_maker.tests.test import run_tests


def test_task():
    from task_maker.tests.utils import TestInterface
    interface = TestInterface("tm", "Testing task-maker", 1, 65536)
    interface.add_solution("solution.py", 100, [5, 20, 20, 55], None)
    interface.add_solution("even.py", 20, [0, 20, 0, 0], None)
    interface.add_solution("odd.py", 20, [0, 0, 20, 0], None)
    interface.run_checks()


if __name__ == "__main__":
    run_tests("tm", __file__)
