#!/usr/bin/python3

import os.path
import shlex
import subprocess
import time

from task_maker.config import Config
from task_maker.task_maker_frontend import Frontend

SERVER_SPAWN_TIME = 3


def get_task_maker_path():
    task_maker = os.path.dirname(__file__)
    task_maker = os.path.join(task_maker, "bin", "task-maker")
    return os.path.abspath(task_maker)


def spawn_backend(type: str, args: str, daemonize: bool):
    task_maker = get_task_maker_path()
    args = shlex.split(args)
    if daemonize:
        args.insert(0, "--daemon")
        streams = subprocess.DEVNULL
    else:
        streams = None
    subprocess.run(
        [task_maker] + args,
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
        print("Spawning server and workers...")
        spawn_server(config)
        time.sleep(SERVER_SPAWN_TIME)
        spawn_worker(config)
        return Frontend(config.host, config.port)
