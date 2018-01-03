#!/usr/bin/env python3

import os
import signal
from typing import Any

import grpc
from proto import manager_pb2_grpc
from proto.manager_pb2 import GetEventsRequest, StopRequest

from python.absolutize import absolutize_request
from python.args import get_parser, UIS
from python.italian_format import get_request


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    os.chdir(args.task_dir)

    if args.clean:
        # TODO: implement the clean process on the manager
        return

    channel = grpc.insecure_channel(args.manager_addr)
    manager = manager_pb2_grpc.TaskMakerManagerStub(channel)

    request = get_request(args)
    absolutize_request(request)

    ui = UIS[args.ui]([os.path.basename(sol.path) for sol in request.solutions])
    ui.set_task_name(os.path.basename(args.task_dir))
    ui.set_time_limit(request.task.time_limit)
    ui.set_memory_limit(request.task.memory_limit_kb)

    last_testcase = 0
    for subtask_num, subtask in enumerate(request.task.subtasks):
        testcases = range(last_testcase, last_testcase + len(subtask.testcases))
        last_testcase += len(subtask.testcases)
        ui.set_subtask_info(subtask_num, subtask.max_score, testcases)

    response = manager.EvaluateTask(request)

    def stop_server(signum: int, _: Any) -> None:
        manager.Stop(StopRequest(evaluation_id=response.id))
        ui.fatal_error("Aborted with sig%d" % signum)
    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    for event in manager.GetEvents(GetEventsRequest(evaluation_id=response.id)):
        ui.from_event(event)
    ui.print_final_status()


if __name__ == '__main__':
    main()
