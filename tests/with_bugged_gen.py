#!/usr/bin/env python

from tests.test import run_tests, TestingUI


def test_task():
    from tests.utils import TestInterface
    interface = TestInterface("with_bugged_gen", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.py")
    interface.set_generation_errors(":(")
    interface.set_fatal_error()
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("with_bugged_gen", __file__)
