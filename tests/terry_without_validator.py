#!/usr/bin/env python3

from proto.event_pb2 import CORRECT, MISSING, WRONG

from tests.test import run_tests, TestingUI


def test_task():
    from tests.utils import TerryTestInterface
    interface = TerryTestInterface("terry_without_validator",
                                   "Testing task-maker",
                                   100)
    interface.set_generator("generator.py")
    interface.set_checker("checker.py")
    interface.add_solution("solution.py", 100, [CORRECT] * 5)
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("terry_without_validator", __file__)
