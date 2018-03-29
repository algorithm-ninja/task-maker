#!/usr/bin/env python3

from proto.event_pb2 import CORRECT, MISSING, WRONG

from tests.test import run_tests, TestingUI


def test_task():
    from tests.utils import TerryTestInterface
    interface = TerryTestInterface("terry_with_bugged_gen",
                                   "Testing task-maker",
                                   100)
    interface.set_generator("generator.py")
    interface.set_validator("validator.py")
    interface.set_checker("checker.py")
    interface.set_fatal_error()
    interface.run_checks(TestingUI.inst)


if __name__ == "__main__":
    run_tests("terry_with_bugged_gen", __file__)
