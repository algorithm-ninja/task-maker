#!/usr/bin/env bash

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export TEST_TMPDIR=/tmp/task_maker_testdir
export PYTHONPATH=$HERE/build/python:$PYTHONPATH
mkdir -p ${TEST_TMPDIR}

cleanup() {
  rm -rf ${TEST_TMPDIR}
}

trap cleanup EXIT

test_sandbox() {
    ( cd $HERE/build/cpp && ./sandbox_unix_test )
    return $?
}

test_task() {
    echo
    echo
    echo
    echo "-------------------- TESTING $1 --------------------"
    python $1.py
    code=$?
    return $code
}

test_all_tasks() {
    ( cd $HERE/python/tests &&
        failed=0
        for task in *.py; do
            task_name=${task%???}
            [ -d "task_$task_name" ] || continue
            test_task $task_name
            failed=$(($failed+$?))
        done
        return $failed
    )
    return $?
}

failed=0

test_sandbox
failed=$(($failed+$?))

test_all_tasks
failed=$(($failed+$?))

echo "Failed: $failed"
exit $failed
