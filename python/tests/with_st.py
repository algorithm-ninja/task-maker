#!/usr/bin/env python3

from task_maker.tests.test import run_tests
from task_maker.uis.ioi import IOIUIInterface


def test_task():
    from task_maker.tests.utils import TestInterface
    interface = TestInterface("with_st", "Testing task-maker", 1, 65536)
    interface.set_generator("generatore.cpp")
    interface.set_validator("valida.py")
    interface.add_solution("soluzione.py", 100, [5, 45, 50],
                           [(1, "Output is correct")] * 6)
    interface.add_solution("bash.sh", 100, [5, 45, 50],
                           [(1, "Output is correct")] * 6)
    interface.add_solution("float_error.cpp", 0, [0, 0, 0],
                           [(0, "signal 8")] * 6)
    interface.add_solution("mle.cpp", 0, [0, 0, 0])
    interface.add_solution("noop.py", 0, [0, 0, 0],
                           [(0, "Some files are missing")] * 6)
    interface.add_solution("nonzero.cpp", 0, [0, 0, 0],
                           [(0, "Exited with code 1")] * 6)
    interface.add_solution("sigsegv.c", 0, [0, 0, 0], [(0, "signal 11")] * 6)
    interface.add_solution(
        "tle.cpp", 50, [5, 45, 0],
        [(1, "Output is correct")] * 4 + [(0, "Time limit exceeded")] * 2)
    interface.add_solution("wa.cpp", 0, [0, 0, 0],
                           [(0, "Output is not correct")] * 6)
    interface.add_solution("wrong_file.cpp", 0, [0, 0, 0],
                           [(0, "Some files are missing")] * 6)
    interface.add_solution("solution.rs", 100, [5, 45, 50],
                           [(1, "Output is correct")] * 6)

    def check_ignored(ui: IOIUIInterface):
        assert ".ignoreme.cpp" not in ui.solutions

    interface.set_callback(check_ignored)
    interface.run_checks()


if __name__ == "__main__":
    run_tests("with_st", __file__)
