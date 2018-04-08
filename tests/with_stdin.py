#!/usr/bin/env python3

from tests.test import run_tests, TestingUI


def test_task():
    from tests.utils import TestInterface
    interface = TestInterface("with_stdin", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.py")
    interface.set_validator("valida.py")
    interface.add_solution("soluzione.cpp", 100, [100],
                           [(1, "Output is correct")] * 4)
    interface.add_solution("noop.py", 0, [0],
                           [(0, "Output is not correct")] * 4)
    interface.add_solution("wa.cpp", 50, [50],
                           [(1, "Output is correct")] * 2 +
                           [(0, "Output is not correct")] * 2)
    interface.add_solution("wrong_file.cpp", 0, [0],
                           [(0, "Output is not correct")] * 4)
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("with_stdin", __file__)
