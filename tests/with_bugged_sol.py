#!/usr/bin/env python3

from tests.test import run_tests, TestingUI
from tests.utils import TestInterface


def test_task():
    interface = TestInterface("with_bugged_sol", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.py")
    interface.set_generation_errors("No buono")
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("with_bugged_sol", __file__)
