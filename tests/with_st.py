#!/usr/bin/env python3

from tests.test import run_tests, TestingUI
from tests.utils import TestInterface


def test_task():
    interface = TestInterface("with_st", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.cpp")
    interface.set_validator("valida.py")
    interface.add_solution("soluzione.py", 100, [5, 45, 50],
                           [(1, "Output is correct")] * 6)
    interface.add_solution("bash.sh", 100, [5, 45, 50],
                           [(1, "Output is correct")] * 6)
    interface.add_solution("float_error.cpp", 0, [0, 0, 0],
                           [(0, "Floating point exception")] * 6)
    interface.add_solution("mle.cpp", 0, [0, 0, 0])
    interface.add_solution("nonzero.cpp", 0, [0, 0, 0],
                           [(0, "Non-zero return code")] * 6)
    interface.add_solution("sigsegv.c", 0, [0, 0, 0],
                           [(0, "Segmentation fault")] * 6)
    interface.add_solution("tle.cpp", 50, [5, 45, 0],
                           [(1, "Output is correct")] * 4 +
                           [(0, "CPU limit exceeded")] * 2)
    interface.add_solution("wa.cpp", 0, [0, 0, 0],
                           [(0, "Output is not correct")] * 6)
    interface.add_solution("wrong_file.cpp", 0, [0, 0, 0],
                           [(0, "Missing output files")] * 6)
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("with_st", __file__)
