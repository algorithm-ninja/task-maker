#!/usr/bin/env python3
import signal

from task_maker.task_maker_frontend import Result, ResultStatus


def result_to_str(result: Result) -> str:
    status = result.status
    if status == ResultStatus.SUCCESS:
        return "Success"
    elif status == ResultStatus.SIGNAL:
        return "Killed with signal %d (%s)" % (
            result.signal, signal.Signals(result.signal).name)
    elif status == ResultStatus.RETURN_CODE:
        return "Exited with code %d" % result.return_code
    elif status == ResultStatus.TIME_LIMIT:
        return "Time limit exceeded"
    elif status == ResultStatus.WALL_LIMIT:
        return "Wall time limit exceeded"
    elif status == ResultStatus.MEMORY_LIMIT:
        return "Memory limit exceeded"
    elif status == ResultStatus.MISSING_FILES:
        return "Some files are missing"
    elif status == ResultStatus.INTERNAL_ERROR:
        return "Internal error: " + result.error
    else:
        raise ValueError(status)
