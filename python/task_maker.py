#!/usr/bin/env python3

from task_maker.syspath_patch import patch_sys_path
patch_sys_path()

import os
import signal
from typing import Any

from manager_pb2 import StopRequest, CleanTaskRequest, ShutdownRequest

from task_maker.formats import ioi_format, terry_format
from task_maker.args import get_parser
from task_maker.detect_format import find_task_dir
from task_maker.manager import get_manager, became_manager, became_server, \
    became_worker


def manager_clean(args):
    request = CleanTaskRequest()
    request.store_dir = os.path.abspath(args.store_dir)
    request.temp_dir = os.path.abspath(args.temp_dir)
    manager = get_manager(args)
    manager.CleanTask(request)


def ioi_format_clean(args):
    ioi_format.clean()
    manager_clean(args)


def terry_format_clean(args):
    terry_format.clean()
    manager_clean(args)


def quit_manager(args, force):
    request = ShutdownRequest()
    request.force = force
    manager = get_manager(args)
    manager.Shutdown(request)


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    if args.run_manager is not None:
        became_manager(args)
    if args.run_server is not None:
        became_server(args)
    if args.run_worker is not None:
        became_worker(args)

    if args.kill_manager:
        quit_manager(args, True)
    if args.quit_manager:
        quit_manager(args, False)
    if args.kill_manager or args.quit_manager:
        return

    task_dir, format = find_task_dir(args.task_dir, args.max_depth)
    if not format:
        raise ValueError(
            "Cannot detect format! It's probable that the task is ill-formed")
    if args.format is not None and format != args.format:
        raise ValueError(
            "Detected format mismatch the required one: %s" % format)

    os.chdir(task_dir)

    if args.clean:
        if format == "ioi":
            ioi_format_clean(args)
        elif format == "terry":
            terry_format_clean(args)
        else:
            raise ValueError("Format %s not supported" % format)
        return

    manager = get_manager(args)

    if format == "ioi":
        request = ioi_format.get_request(args)
        solutions = [os.path.basename(sol.path) for sol in request.solutions]
    elif format == "terry":
        request = terry_format.get_request(args)
        solutions = [
            os.path.basename(sol.solution.path) for sol in request.solutions
        ]
    else:
        raise ValueError("Format %s not supported" % format)

    ui = args.ui.value(solutions, format)

    if format == "ioi":
        ui.set_task_name("%s (%s)" % (request.task.title, request.task.name))
        ui.set_time_limit(request.task.time_limit)
        ui.set_memory_limit(request.task.memory_limit_kb)

        last_testcase = 0
        for subtask_num, subtask in request.task.subtasks.items():
            last_testcase += len(subtask.testcases)
            ui.set_subtask_info(subtask_num, subtask.max_score,
                                sorted(subtask.testcases.keys()))
        ui.set_max_score(
            sum(subtask.max_score
                for subtask in request.task.subtasks.values()))
    elif format == "terry":
        ui.set_task_name("%s (%s)" % (request.task.title, request.task.name))
        ui.set_max_score(request.task.max_score)
    else:
        raise ValueError("Format %s not supported" % format)

    eval_id = None

    def stop_server(signum: int, _: Any) -> None:
        if eval_id:
            ui.stop("Waiting the manager to complete the last job")
            manager.Stop(StopRequest(evaluation_id=eval_id))
        ui.fatal_error("Aborted with sig%d" % signum)

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    if format == "ioi":
        events = manager.EvaluateTask(request)
    elif format == "terry":
        events = manager.EvaluateTerryTask(request)
    else:
        raise NotImplementedError("Format %s not supported" % format)

    for event in events:
        event_type = event.WhichOneof("event_oneof")
        if event_type == "evaluation_started":
            eval_id = event.evaluation_started.id
        elif event_type == "evaluation_ended":
            eval_id = None
        ui.from_event(event)
    ui.print_final_status()


if __name__ == '__main__':
    main()
