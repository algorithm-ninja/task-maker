#!/usr/bin/env python3

import os
import signal
from typing import Any

from proto.manager_pb2 import StopRequest, CleanTaskRequest, ShutdownRequest

from python import ioi_format, terry_format
from python.args import get_parser, UIS
from python.detect_format import detect_format
from python.manager import get_manager


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

    os.chdir(args.task_dir)

    if not args.format:
        args.format = detect_format()
    if not args.format:
        raise ValueError(
            "Cannot autodetect format! Try to pass --format to explicitly set "
            "it. It's probable that the task is ill-formed")

    if args.clean:
        if args.format == "ioi":
            ioi_format_clean(args)
        elif args.format == "terry":
            terry_format_clean(args)
        else:
            raise ValueError("Format %s not supported" % args.format)

    if args.kill_manager:
        quit_manager(args, True)
    if args.quit_manager:
        quit_manager(args, False)

    if args.quit_manager or args.kill_manager or args.clean:
        return

    manager = get_manager(args)

    if args.format == "ioi":
        request = ioi_format.get_request(args)
        solutions = [os.path.basename(sol.path) for sol in request.solutions]
    elif args.format == "terry":
        request = terry_format.get_request(args)
        solutions = [os.path.basename(sol.solution.path) for sol in
                     request.solutions]
    else:
        raise ValueError("Format %s not supported" % args.format)

    ui = UIS[args.ui](solutions, args.format)

    if args.format == "ioi":
        ui.set_task_name("%s (%s)" % (request.task.title, request.task.name))
        ui.set_time_limit(request.task.time_limit)
        ui.set_memory_limit(request.task.memory_limit_kb)

        last_testcase = 0
        for subtask_num, subtask in request.task.subtasks.items():
            last_testcase += len(subtask.testcases)
            ui.set_subtask_info(subtask_num, subtask.max_score,
                                sorted(subtask.testcases.keys()))
        ui.set_max_score(sum(subtask.max_score for subtask in
                             request.task.subtasks.values()))
    elif args.format == "terry":
        ui.set_task_name("%s (%s)" % (request.task.title, request.task.name))
        ui.set_max_score(request.task.max_score)
    else:
        raise ValueError("Format %s not supported" % args.format)

    eval_id = None

    def stop_server(signum: int, _: Any) -> None:
        if eval_id:
            ui.stop("Waiting the manager to complete the last job")
            manager.Stop(StopRequest(evaluation_id=eval_id))
        ui.fatal_error("Aborted with sig%d" % signum)

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    if args.format == "ioi":
        events = manager.EvaluateTask(request)
    elif args.format == "terry":
        events = manager.EvaluateTerryTask(request)
    else:
        raise NotImplementedError("Format %s not supported" % args.format)

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
