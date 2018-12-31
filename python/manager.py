#!/usr/bin/env python3

import time

import os.path
import signal
import subprocess
from task_maker.config import Config
from task_maker.task_maker_frontend import Frontend
from typing import List

SERVER_SPAWN_TIME = 1
MAX_SPAWN_ATTEMPT = 3


def get_task_maker_path():
    """
    Get the path of the cpp executable
    """
    task_maker = os.path.dirname(__file__)
    task_maker = os.path.join(task_maker, "bin", "task-maker")
    return os.path.abspath(task_maker)


def spawn_backend(type: str, args: List[str], daemonize: bool):
    """
    Spawn a backend service, eventually daemonizing it
    """
    task_maker = get_task_maker_path()
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
    """
    Spawn the server, passing its arguments from the config
    """
    args = []
    if config.server_logfile is not None:
        args += ["--logfile", config.server_logfile]
    if config.server_pidfile is not None:
        args += ["--pidfile", config.server_pidfile]
    if config.storedir is not None:
        args += ["--store-dir", config.storedir]
    if config.tempdir is not None:
        args += ["--temp-dir", config.tempdir]
    if config.cache_size is not None:
        args += ["--cache-size", str(config.cache_size)]
    if config.server_address is not None:
        args += ["--address", config.server_address]
    if config.server_port is not None:
        args += ["--port", str(config.server_port)]
    if config.server_verbose:
        args += ["--verbose"]
    spawn_backend("server", args, not config.run_server)


def spawn_worker(config: Config):
    """
    Spawn the worker, passing its arguments from the config
    """
    args = []
    if config.worker_logfile is not None:
        args += ["--logfile", config.worker_logfile]
    if config.worker_pidfile is not None:
        args += ["--pidfile", config.worker_pidfile]
    if config.storedir is not None:
        args += ["--store-dir", config.storedir]
    if config.tempdir is not None:
        args += ["--temp-dir", config.tempdir]
    if config.cache_size is not None:
        args += ["--cache-size", str(config.cache_size)]
    if config.worker_keep_sandboxes:
        args += ["--keep_sandboxes"]
    if config.worker_name is not None:
        args += ["--name", config.worker_name]
    if config.worker_num_cores is not None:
        args += ["--num-cores", str(config.worker_num_cores)]
    if config.worker_port is not None:
        args += ["--port", str(config.worker_port)]
    if config.worker_address is not None:
        args += ["--server", config.worker_address]
    if config.worker_pending_requests is not None:
        args += ["--pending-requests", str(config.worker_pending_requests)]
    if config.worker_verbose:
        args += ["--verbose"]
    spawn_backend("worker", args, not config.run_worker)


def get_frontend(config: Config) -> Frontend:
    """
    Run the frontend module connecting to the server and eventually spawning it
    if needed.
    """
    try:
        return Frontend(config.host, config.port)
    except:
        if config.no_spawn:
            raise RuntimeError(
                "Cannot connect to the server and spawning is forbidden")
        spawn_server(config)
        print("Spawning server and workers", end="", flush=True)
        for _ in range(3):
            print(".", end="", flush=True)
            time.sleep(SERVER_SPAWN_TIME / 3)
        print()
        spawn_worker(config)
        for t in range(MAX_SPAWN_ATTEMPT):
            try:
                return Frontend(config.host, config.port)
            except:
                print("Attempt {} failed".format(t + 1))
                time.sleep(1)
        raise RuntimeError("Failed to spawn the server")


def stop():
    proc = subprocess.run(["ps", "ax", "-o", "pid,cmd"],
                          stdout=subprocess.PIPE)
    path = get_task_maker_path()
    running = [p.split()[:2] for p in proc.stdout.decode().splitlines()]
    pids = [int(pid) for pid, proc in running if proc == path]
    for pid in pids:
        print("Sending SIGTERM to pid %d" % pid)
        os.kill(pid, signal.SIGTERM)
