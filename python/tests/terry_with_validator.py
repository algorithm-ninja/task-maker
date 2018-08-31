#!/usr/bin/env python3

from task_maker.tests.test import run_tests
from task_maker.uis.terry import TestcaseStatus


def test_task():
    from task_maker.tests.utils import TerryTestInterface

    interface = TerryTestInterface("terry_with_validator",
                                   "Testing task-maker", 100)
    interface.set_generator("generator.py")
    interface.set_validator("validator.py")
    interface.set_checker("checker.py")
    interface.add_solution("solution.py", 100, [TestcaseStatus.CORRECT] * 5)
    interface.add_solution("unordered.py", 100, [TestcaseStatus.CORRECT] * 5)
    interface.add_solution("wrong.py", 0, [TestcaseStatus.WRONG] * 5)
    interface.add_solution("missing.py", 0, [TestcaseStatus.MISSING] * 5)
    interface.add_solution("partial.py", 40, [
        TestcaseStatus.CORRECT, TestcaseStatus.CORRECT, TestcaseStatus.WRONG,
        TestcaseStatus.MISSING, TestcaseStatus.MISSING
    ])
    interface.run_checks()


if __name__ == "__main__":
    run_tests("terry_with_validator", __file__)
