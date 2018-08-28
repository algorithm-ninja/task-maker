#!/usr/bin/env python3

from task_maker.tests.test import run_tests


def test_task():
    from task_maker.tests.utils import TestInterface
    interface = TestInterface("communication", "Testing task-maker", 1, 65536)
    message = "A-ha, you're the best adding program I've ever met!"
    interface.add_solution("solution.c", 100, [100],
                           [(1, message)] * 3)
    interface.add_solution("solution.cpp", 100, [100],
                           [(1, message)] * 3)
    interface.add_solution("solution.pas", 100, [100],
                           [(1, message)] * 3)
    interface.run_checks()


if __name__ == "__main__":
    run_tests("communication", __file__)
