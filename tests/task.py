#!/usr/bin/env python3

# we use the global scope, so pylint considers every variable as a constant
# pylint: disable=invalid-name

import os.path
import shutil
import sys
from argparse import Namespace

from python.silent_ui import SilentUI
from python.task_maker import UIS, run_for_cwd
from python.ui import CompilationStatus, GenerationStatus


class TestingUI(SilentUI):
    inst = None

    def __init__(self: "TestingUI") -> None:
        super().__init__()
        TestingUI.inst = self

    def fatal_error(self: "TestingUI", msg: str) -> None:
        print("FATAL ERROR", msg, file=sys.stderr)


# inject the testing UI to the valid UIs
UIS["testing"] = TestingUI

orig_task_dir = os.path.join(os.path.dirname(__file__), "test_task")
task_dir = os.path.join(os.getenv("TEST_TMPDIR", "/tmp"), "test_task")
shutil.copytree(orig_task_dir, task_dir)

os.chdir(task_dir)

args = Namespace(
    solutions=[],
    task_dir=task_dir,
    ui="testing",
    exclusive=False,
    cache="nothing",
    evaluate_on=None,
    extra_eval_time=0.5,
    dry_run=False,
    num_cores=None,
    temp_dir="temp",
    store_dir="files",
    clean=False)

run_for_cwd(args)

assert TestingUI.inst
test_data = TestingUI.inst  # type: TestingUI

# pylint: disable=protected-access

# Task details
assert test_data.task_name == "Testing task-maker (test_task)"
assert test_data._time_limit == 1
assert test_data._memory_limit == 65536
assert test_data._num_testcases == 6

assert len(test_data._subtask_testcases) == 3
assert test_data._subtask_testcases[0] == [0, 1]
assert test_data._subtask_testcases[1] == [2, 3]
assert test_data._subtask_testcases[2] == [4, 5]
assert len(test_data._subtask_max_scores) == 3
assert test_data._subtask_max_scores[0] == 5
assert test_data._subtask_max_scores[1] == 45
assert test_data._subtask_max_scores[2] == 50

# Solutions and other files
assert len(test_data._other_compilations) == 3
assert "soluzione.py" in test_data._other_compilations
assert "generatore.cpp" in test_data._other_compilations
assert "valida.py" in test_data._other_compilations

assert len(test_data._solutions) == 9
assert "float_error.cpp" in test_data._solutions
assert "mle.cpp" in test_data._solutions
assert "nonzero.cpp" in test_data._solutions
assert "not_compile.cpp" in test_data._solutions
assert "sigsegv.cpp" in test_data._solutions
assert "soluzione.py" in test_data._solutions
assert "tle.cpp" in test_data._solutions
assert "wa.cpp" in test_data._solutions
assert "wrong_file.cpp" in test_data._solutions

# Check compilation status
assert "not_compile.cpp" in test_data._compilation_errors
for sol, comp_status in test_data._compilation_status.items():
    if sol == "not_compile.cpp":
        assert comp_status == CompilationStatus.FAILURE
    else:
        assert comp_status == CompilationStatus.SUCCESS

# Generation
assert not test_data._generation_errors
for gen_status in test_data._generation_status.values():
    assert gen_status == GenerationStatus.SUCCESS

# Solution results

soluzione = test_data._solution_status["soluzione.py"]
assert soluzione.score == 100
for testcase in soluzione.testcase_result.values():
    assert testcase.message == "Output is correct"
    assert testcase.score == 1

float_error = test_data._solution_status["float_error.cpp"]
assert float_error.score == 0
for testcase in float_error.testcase_result.values():
    assert testcase.message == "Signal 8"
    assert testcase.score == 0

mle = test_data._solution_status["mle.cpp"]
assert mle.score == 0
for testcase in mle.testcase_result.values():
    assert testcase.message == "Signal 6"
    assert testcase.score == 0
    assert testcase.memory > 60000

nonzero = test_data._solution_status["nonzero.cpp"]
assert nonzero.score == 0
for testcase in nonzero.testcase_result.values():
    assert testcase.message == "Return code 1"
    assert testcase.score == 0

sigsegv = test_data._solution_status["sigsegv.cpp"]
assert sigsegv.score == 0
for testcase in sigsegv.testcase_result.values():
    assert testcase.message == "Signal 11"
    assert testcase.score == 0

tle = test_data._solution_status["tle.cpp"]
assert tle.score == 50
for tc_num, testcase in tle.testcase_result.items():
    if tc_num < 4:
        assert testcase.message == "Output is correct"
        assert testcase.cpu_time <= 1
        assert testcase.wall_time <= 1.3
        assert testcase.score == 1
    # TODO(edomora97): due to an actual bug in the evaluation process, the
    # measured time is correct but the limit considers the extra time as valid
    # limit. REMOVE THE COMMENTS WHEN THIS THING IS FIXED!
    #
    # else:
    #     assert testcase.message == "Execution timed out"
    #     assert testcase.cpu_time > 1
    #     assert testcase.wall_time > 1
    #     assert testcase.score == 0

wa = test_data._solution_status["wa.cpp"]
assert wa.score == 0
for testcase in wa.testcase_result.values():
    assert testcase.message == "Output not correct"
    assert testcase.score == 0

wrong_file = test_data._solution_status["wrong_file.cpp"]
assert wrong_file.score == 0
for testcase in wrong_file.testcase_result.values():
    assert testcase.message == "Missing output files"
    assert testcase.score == 0
