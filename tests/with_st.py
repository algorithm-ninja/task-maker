#!/usr/bin/env python3

# we use the global scope, so pylint considers every variable as a constant
# pylint: disable=invalid-name

from proto.event_pb2 import FAILURE, DONE

from tests.test import run_tests, TestingUI


# pylint: disable=protected-access


def test_task_details() -> None:
    test_data = TestingUI.inst
    assert test_data.task_name == "Testing task-maker (with_st)"
    assert test_data._time_limit == 1
    assert test_data._memory_limit == 65536
    assert test_data._num_testcases == 6

    assert len(test_data._subtask_testcases) == 3
    assert list(test_data._subtask_testcases[0]) == [0, 1]
    assert list(test_data._subtask_testcases[1]) == [2, 3]
    assert list(test_data._subtask_testcases[2]) == [4, 5]
    assert len(test_data._subtask_max_scores) == 3
    assert test_data._subtask_max_scores[0] == 5
    assert test_data._subtask_max_scores[1] == 45
    assert test_data._subtask_max_scores[2] == 50


def test_solution_files() -> None:
    test_data = TestingUI.inst
    assert len(test_data._other_compilations) == 2
    assert "generatore.cpp" in test_data._other_compilations
    assert "valida.py" in test_data._other_compilations

    assert len(test_data.solutions) == 10
    assert "bash.sh" in test_data.solutions
    assert "float_error.cpp" in test_data.solutions
    assert "mle.cpp" in test_data.solutions
    assert "nonzero.cpp" in test_data.solutions
    assert "not_compile.cpp" in test_data.solutions
    assert "sigsegv.c" in test_data.solutions
    assert "soluzione.py" in test_data.solutions
    assert "tle.cpp" in test_data.solutions
    assert "wa.cpp" in test_data.solutions
    assert "wrong_file.cpp" in test_data.solutions


def test_compilation_status() -> None:
    test_data = TestingUI.inst
    assert "not_compile.cpp" in test_data._compilation_errors
    for sol, comp_status in test_data._compilation_status.items():
        if sol == "not_compile.cpp":
            assert comp_status == FAILURE
            errors = test_data._compilation_errors[sol]
            assert "does not name a type" in errors
        else:
            assert (sol, comp_status) == (sol, DONE)


def test_generation() -> None:
    test_data = TestingUI.inst
    assert not test_data._generation_errors
    for gen_status in test_data._generation_status.values():
        assert gen_status == DONE


def test_solutions() -> None:
    test_data = TestingUI.inst
    soluzione = test_data._solution_status["soluzione.py"]
    assert soluzione.score == 100
    for testcase in soluzione.testcase_result.values():
        assert testcase.message == "Output is correct"
        assert testcase.score == 1

    bash = test_data._solution_status["bash.sh"]
    assert bash.score == 100
    for testcase in bash.testcase_result.values():
        assert testcase.message == "Output is correct"
        assert testcase.score == 1

    float_error = test_data._solution_status["float_error.cpp"]
    assert float_error.score == 0
    for testcase in float_error.testcase_result.values():
        assert testcase.message == "Floating point exception"
        assert testcase.score == 0

    mle = test_data._solution_status["mle.cpp"]
    assert mle.score == 0
    for testcase in mle.testcase_result.values():
        # in my machine the program is aborted hitting the memory limit
        # (it throws a std::bad_alloc)
        assert testcase.message == "Memory limit exceeded" or \
            testcase.message == "Aborted"
        assert testcase.score == 0
        assert testcase.memory_used_kb > 60000

    nonzero = test_data._solution_status["nonzero.cpp"]
    assert nonzero.score == 0
    for testcase in nonzero.testcase_result.values():
        assert testcase.message == "Non-zero return code"
        assert testcase.score == 0

    sigsegv = test_data._solution_status["sigsegv.c"]
    assert sigsegv.score == 0
    for testcase in sigsegv.testcase_result.values():
        assert testcase.message == "Segmentation fault"
        assert testcase.score == 0

    tle = test_data._solution_status["tle.cpp"]
    assert tle.score == 50
    for tc_num, testcase in tle.testcase_result.items():
        if tc_num < 4:
            assert testcase.message == "Output is correct"
            assert testcase.cpu_time_used <= 1
            assert testcase.wall_time_used <= 1.3
            assert testcase.score == 1
        else:
            assert testcase.message == "CPU limit exceeded"
            assert testcase.cpu_time_used > 1
            assert testcase.wall_time_used > 1
            assert testcase.score == 0

    wa = test_data._solution_status["wa.cpp"]
    assert wa.score == 0
    for testcase in wa.testcase_result.values():
        assert testcase.message == "Output is not correct"
        assert testcase.score == 0

    wrong_file = test_data._solution_status["wrong_file.cpp"]
    assert wrong_file.score == 0
    for testcase in wrong_file.testcase_result.values():
        assert testcase.message == "Missing output files"
        assert testcase.score == 0


if __name__ == "__main__":
    run_tests("with_st", __file__)
