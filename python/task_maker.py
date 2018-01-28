#!/usr/bin/env python3

import multiprocessing
import os
import signal
import subprocess
import time
from typing import Any

import daemon
import grpc
from proto import manager_pb2_grpc
from proto.manager_pb2 import GetEventsRequest, StopRequest, CleanTaskRequest

from python.absolutize import absolutize_request
from python.args import get_parser, UIS
from python.italian_format import get_request, clean


def manager_process(pipe: Any, manager: str, port: int) -> None:
    try:
        manager_proc = subprocess.Popen(
            [manager, "--port", str(port)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        pipe.send(None)
    except Exception as exc:  # pylint: disable=broad-except
        pipe.send(exc)
    with daemon.DaemonContext(detach_process=True, working_directory="/tmp"):
        manager_proc.wait()


def spawn_manager(port: int) -> None:
    manager = os.path.dirname(__file__)
    manager = os.path.join(manager, "..", "manager", "manager")
    manager = os.path.abspath(manager)
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=manager_process, args=(child_conn, manager, port))
    proc.start()
    exc = parent_conn.recv()
    if exc:
        raise exc
    proc.join()


def get_manager(args):
    manager_spawned = False
    max_attempts = 100
    for attempt in range(max_attempts):
        try:
            channel = grpc.insecure_channel(
                "localhost:" + str(args.manager_port))
            return manager_pb2_grpc.TaskMakerManagerStub(channel)
        except grpc._channel._Rendezvous as e:
            if e.code() != grpc.StatusCode.UNAVAILABLE:
                raise
            if not manager_spawned:
                spawn_manager(args.manager_port)
                manager_spawned = True
            if attempt == max_attempts - 1:
                raise
            del channel
            time.sleep(0.5)


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    os.chdir(args.task_dir)

    if args.clean:
        clean()
        request = CleanTaskRequest()
        request.store_dir = os.path.abspath(args.store_dir)
        request.temp_dir = os.path.abspath(args.temp_dir)
        manager = get_manager(args)
        manager.CleanTask(request)
        return

    request = get_request(args)
    absolutize_request(request)

    ui = UIS[args.ui](
        [os.path.basename(sol.path) for sol in request.solutions])
    ui.set_task_name("%s (%s)" % (request.task.title, request.task.name))
    ui.set_time_limit(request.task.time_limit)
    ui.set_memory_limit(request.task.memory_limit_kb)

    last_testcase = 0
    for subtask_num, subtask in request.task.subtasks.items():
        last_testcase += len(subtask.testcases)
        ui.set_subtask_info(subtask_num, subtask.max_score,
                            sorted(subtask.testcases.keys()))

    manager = get_manager(args)
    response = manager.EvaluateTask(request)

    def stop_server(signum: int, _: Any) -> None:
        manager.Stop(StopRequest(evaluation_id=response.id))
        ui.fatal_error("Aborted with sig%d" % signum)

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    for event in manager.GetEvents(
            GetEventsRequest(evaluation_id=response.id)):
        ui.from_event(event)
    ui.print_final_status()


if __name__ == '__main__':
    main()
