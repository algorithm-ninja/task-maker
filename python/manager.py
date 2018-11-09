#!/usr/bin/env python3

import os.path
import shlex
import subprocess
import time

from task_maker.config import Config
from task_maker.task_maker_frontend import Frontend

SERVER_SPAWN_TIME = 1
MAX_SPAWN_ATTEMPT = 3


def get_task_maker_path():
    task_maker = os.path.dirname(__file__)
    task_maker = os.path.join(task_maker, "bin", "task-maker")
    return os.path.abspath(task_maker)


def spawn_backend(type: str, args: str, daemonize: bool):
    task_maker = get_task_maker_path()
    args = shlex.split(args)
    if daemonize:
        args.append("--daemon")
        streams = subprocess.DEVNULL
    else:
        streams = None
    subprocess.run(
        [task_maker, type] + args,
        stdin=streams,
        stdout=streams,
        stderr=streams)


def spawn_server(config: Config):
    spawn_backend("server", config.server_args, not config.run_server)


def spawn_worker(config: Config):
    spawn_backend("worker", config.worker_args, not config.run_worker)


def get_frontend(config: Config) -> Frontend:
    try:
        return Frontend(config.host, config.port)
    except:
        spawn_server(config)
        print("Spawning server and workers", end="", flush=True)
        for _ in range(3):
            print(".", end="", flush=True)
            time.sleep(SERVER_SPAWN_TIME/3)
        print()
        spawn_worker(config)
        for t in range(MAX_SPAWN_ATTEMPT):
            try:
                return Frontend(config.host, config.port)
            except:
                print("Attempt {} failed".format(t+1))
                time.sleep(1)
        raise RuntimeError("Failed to spawn the server")
