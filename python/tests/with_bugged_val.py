#!/usr/bin/env python3

from task_maker.tests.test import run_tests


def test_task():
    from task_maker.tests.utils import TestInterface
    interface = TestInterface("with_bugged_val", "Testing task-maker", 1,
                              65536)
    interface.set_generator("generatore.py")
    interface.set_validator("valida.py")
    interface.set_validation_errors("AssertionError")
    interface.run_checks()


if __name__ == "__main__":
    run_tests("with_bugged_val", __file__)
