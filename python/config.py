#!/usr/bin/env python3
import os
from typing import List, Optional
import pytoml

from task_maker.args import CacheMode, UIS, TaskFormat, Arch


class Config:
    OPTIONS = {
        "generic": [
            "solutions", "task_dir", "max_depth", "ui", "cache", "dry_run",
            "clean", "format"
        ],
        "remote":
        ["server", "run_server", "run_worker", "server_args", "worker_args"],
        "execution": ["exclusive", "extra_time", "copy_exe"],
        "ioi": ["detailed_checker"],
        "terry": ["arch", "seed"],
        "help": ["help_colors"],
        "bulk": ["contest_dir", "contest_yaml"]
    }
    CUSTOM_TYPES = {
        "ui": UIS,
        "cache": CacheMode,
        "format": TaskFormat,
        "arch": Arch
    }

    def __init__(self):
        # generic group
        self.solutions = []  # type: List[str]
        self.task_dir = os.getcwd()
        self.max_depth = 2
        self.ui = UIS.CURSES
        self.cache = CacheMode.ALL
        self.dry_run = False
        self.clean = False
        self.format = None  # type: Optional[TaskFormat]

        # remote group
        self.server = "127.0.0.1:7070"  # type: str
        self.run_server = False
        self.run_worker = False
        self.server_args = "--port=7070"
        self.worker_args = "--name=local --server=127.0.0.1:7070"
        self._get_host_port()

        # execution group
        self.exclusive = False
        self.extra_time = 0.0
        self.copy_exe = False

        # IOI group
        self.detailed_checker = False

        # terry group
        self.arch = Arch.DEFAULT
        self.seed = None

        # help group
        self.help_colors = False

        # bulk group
        self.contest_dir = os.getcwd()
        self.contest_yaml = None
        # current index in bulk run and total number of bulk tasks
        self.bulk_number = None  # type: Optional[int]
        self.bulk_total = None  # type: Optional[int]

    def apply_args(self, args):
        for group, options in Config.OPTIONS.items():
            for arg in options:
                self._apply_arg(arg, args)
        self._get_host_port()

    def apply_file(self):
        path = os.path.join(os.path.expanduser("~"), ".task-maker.toml")
        try:
            with open(path, "r") as f:
                config = pytoml.loads(f.read())
        except FileNotFoundError:
            return
        for group, items in config.items():
            if group not in Config.OPTIONS:
                raise ValueError("Invalid group specified in config file: " +
                                 group)
            for item, value in items.items():
                if item not in Config.OPTIONS[group]:
                    raise ValueError(
                        "Invalid option in config.file: {}.{}".format(
                            group, item))
                setattr(self, item, self._get_value(group, item, value))
        self._get_host_port()

    def _apply_arg(self, name, args):
        value = getattr(args, name)
        if value is not None and value is not False:
            setattr(self, name, value)

    def _get_host_port(self):
        server_addr = self.server.split(":")
        if len(server_addr) == 1:
            self.host, self.port = server_addr[0], 7071
        elif len(server_addr) == 2:
            self.host, self.port = server_addr[0], int(server_addr[1])
        else:
            raise ValueError("Invalid address for the server")

    def _get_value(self, group, item, value):
        if item in Config.CUSTOM_TYPES:
            try:
                return Config.CUSTOM_TYPES[item](value)
            except Exception:
                valid = [x.name.lower() for x in Config.CUSTOM_TYPES[item]]
                raise ValueError("Invalid config value at {}.{}, "
                                 "the valid values are: {}".format(
                                     group, item, ", ".join(valid)))
