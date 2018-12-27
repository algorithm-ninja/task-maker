#!/usr/bin/env python3
from enum import Enum
from task_maker.task_maker_frontend import Result, Resources, ResultStatus
from typing import Optional, Dict


def enum_to_str(val: Enum) -> Optional[str]:
    if val is None:
        return None
    return str(val).split(".")[-1]


def resources_to_dict(res: Optional[Resources]) -> Optional[dict]:
    if res is None:
        return None
    return {
        "cpu_time": res.cpu_time,
        "sys_time": res.sys_time,
        "wall_time": res.wall_time,
        "memory": res.memory
    }


def result_to_dict(res: Optional[Result]) -> Optional[dict]:
    if res is None:
        return None
    return {
        "status":
            enum_to_str(res.status),
        "signal":
            res.signal if res.status == ResultStatus.SIGNAL else None,
        "return_code":
            res.return_code if res.status == ResultStatus.RETURN_CODE else None,
        "error":
            res.error if res.status == ResultStatus.INTERNAL_ERROR else None,
        "resources":
            resources_to_dict(res.resources),
        "was_cached":
            res.was_cached,
        "was_killed":
            res.was_killed
    }


def get_compilations(files: Dict[str, "SourceFileCompilationResult"]):
    return {
        name: {
            "status": enum_to_str(compilation.status),
            "stderr": compilation.stderr,
            "result": result_to_dict(compilation.result)
        }
        for name, compilation in files.items()
    }
