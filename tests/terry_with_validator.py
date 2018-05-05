#!/usr/bin/env python3

from event_pb2 import CORRECT, MISSING, WRONG

from tests.test import run_tests, TestingUI


def test_task():
    from tests.utils import TerryTestInterface
    interface = TerryTestInterface("terry_with_validator", "Testing task-maker",
                                   100)
    interface.set_generator("generator.py")
    interface.set_validator("validator.py")
    interface.set_checker("checker.py")
    interface.add_solution("solution.py", 100, [CORRECT] * 5)
    interface.add_solution("unordered.py", 100, [CORRECT] * 5)
    interface.add_solution("wrong.py", 0, [WRONG] * 5)
    interface.add_solution("missing.py", 0, [MISSING] * 5)
    interface.add_solution("partial.py", 40, [CORRECT, CORRECT, WRONG,
                                              MISSING, MISSING])
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("terry_with_validator", __file__)
