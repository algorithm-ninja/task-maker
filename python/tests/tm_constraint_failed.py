#!/usr/bin/env python3

from task_maker.tests.test import run_tests

if __name__ == "__main__":
    try:
        run_tests("tm_constraint_failed", __file__)
    except Exception as ex:
        assert "Constraint not met" in str(ex)
    else:
        raise ValueError("Constraint failed not thrown")
