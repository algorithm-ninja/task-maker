#!/usr/bin/python3

import multiprocessing
import subprocess
import time
from typing import Any

import daemon
import grpc
import os.path

from proto import manager_pb2_grpc


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
    max_attempts = 10
    connect_timeout = 1
    for attempt in range(max_attempts):
        channel = grpc.insecure_channel(
            "localhost:" + str(args.manager_port))
        ready_future = grpc.channel_ready_future(channel)
        try:
            ready_future.result(timeout=connect_timeout)
        except grpc.FutureTimeoutError:
            print("Spawning manager...")
            if not manager_spawned:
                spawn_manager(args.manager_port)
                manager_spawned = True
            time.sleep(0.5)
        else:
            return manager_pb2_grpc.TaskMakerManagerStub(channel)
    raise RuntimeError("Failed to spawn the manager")