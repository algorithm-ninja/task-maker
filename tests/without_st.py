#!/usr/bin/env python

from tests.test import run_tests, TestingUI


def test_task():
    from tests.utils import TestInterface
    interface = TestInterface("without_st", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.py")
    interface.set_validator("valida.py")
    interface.add_solution("soluzione.py", 100, [100],
                           [(1, "Output is correct")] * 6)
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("without_st", __file__)
