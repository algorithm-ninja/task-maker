#!/usr/bin/env python3

from tests.test import run_tests, TestingUI
from tests.utils import TestInterface


def test_task():
    interface = TestInterface("with_checker", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.py")
    interface.set_validator("valida.py")
    interface.add_solution("soluzione.sh", 100, [100], [(1, "Ok!")] * 6)
    interface.add_solution("wrong.sh", 0, [0], [(0, "Ko!")] * 6)
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("with_checker", __file__)
