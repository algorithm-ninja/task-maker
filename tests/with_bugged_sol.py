#!/usr/bin/env python3

# we use the global scope, so pylint considers every variable as a constant
# pylint: disable=invalid-name

from proto.event_pb2 import FAILURE

from tests.test import run_tests, TestingUI


# pylint: disable=protected-access


def test_task_details() -> None:
    test_data = TestingUI.inst
    assert test_data.task_name == "Testing task-maker (with_bugged_sol)"
    assert test_data._time_limit == 1
    assert test_data._memory_limit == 65536
    assert test_data._num_testcases == 1

    assert len(test_data._subtask_testcases) == 1
    assert list(test_data._subtask_testcases[0]) == [0]
    assert len(test_data._subtask_max_scores) == 1
    assert test_data._subtask_max_scores[0] == 100


def test_generation() -> None:
    test_data = TestingUI.inst
    assert test_data._generation_errors
    for gen_error in test_data._generation_errors.values():
        assert "No buono" in gen_error
    for gen_status in test_data._generation_status.values():
        assert gen_status == FAILURE


if __name__ == "__main__":
    run_tests("with_bugged_sol", __file__)
