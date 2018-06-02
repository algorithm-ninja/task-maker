#!/usr/bin/python3

import os.path
import subprocess
import time

import grpc
import manager_pb2_grpc


def get_task_maker_path():
    task_maker = os.path.dirname(__file__)
    task_maker = os.path.join(task_maker, "bin", "task-maker")
    return os.path.abspath(task_maker)


def spawn_manager(port: int) -> None:
    manager = get_task_maker_path()
    subprocess.run(
        [manager, "-mode", "manager", "-port",
         str(port), "-daemon"])


def get_manager(args):
    manager_spawned = False
    max_attempts = 10
    connect_timeout = 1
    for attempt in range(max_attempts):
        channel = grpc.insecure_channel("localhost:" + str(args.manager_port))
        ready_future = grpc.channel_ready_future(channel)
        try:
            ready_future.result(timeout=connect_timeout)
        except grpc.FutureTimeoutError:
            if not manager_spawned:
                print("Spawning manager...")
                spawn_manager(args.manager_port)
                manager_spawned = True
            time.sleep(0.5)
        else:
            return manager_pb2_grpc.TaskMakerManagerStub(channel)
    raise RuntimeError("Failed to spawn the manager")


def became_manager(args):
    print("Spawning manager")
    manager_args = args.run_manager
    os.execv(
        get_task_maker_path(),
        ["task-maker", "-mode", "manager", "-port", "7071"] + manager_args)


def became_server(args):
    print("Spawning server")
    server_args = args.run_server
    os.execv(get_task_maker_path(),
             ["task-maker", "-mode", "server"] + server_args)


def became_worker(args):
    print("Spawning worker")
    worker_args = args.run_worker
    os.execv(get_task_maker_path(),
             ["task-maker", "-mode", "worker"] + worker_args)
