#!/usr/bin/env python3
import os
import pytoml
from task_maker.args import CacheMode, UIS, TaskFormat, Arch
from typing import List, Optional, Tuple


class Config:
    OPTIONS = {
        "generic": [
            "solutions", "task_dir", "max_depth", "ui", "cache", "dry_run",
            "clean", "task_info", "format", "fuzz_checker"
        ],
        "remote": [
            "server", "run_server", "run_worker", "storedir", "tempdir",
            "cache_size"
        ],
        "server": [
            "server_logfile", "server_pidfile", "server_address",
            "server_port", "server_verbose"
        ],
        "worker": [
            "worker_logfile", "worker_pidfile", "worker_keep_sandboxes",
            "worker_name", "worker_num_cores", "worker_port", "worker_address",
            "worker_pending_requests", "worker_verbose"
        ],
        "execution": ["exclusive", "extra_time", "copy_exe"],
        "ioi": ["detailed_checker"],
        "terry": ["arch", "seed"],
        "statement": ["no_statement", "set"],
        "help": ["help_colors"],
        "bulk": ["contest_dir", "contest_yaml", "make_booklet"]
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
        self.cwd = os.getcwd()
        # $PWD for tasks inside symlinks
        self.task_dir = os.getenv("PWD", os.getcwd())
        self.max_depth = 2
        self.ui = UIS.CURSES
        self.cache = CacheMode.ALL
        self.dry_run = False
        self.clean = False
        self.task_info = False
        self.format = None  # type: Optional[TaskFormat]
        self.fuzz_checker = None  # type: Tuple[str, str]

        # remote group
        self.server = "127.0.0.1:7070"
        self.run_server = False
        self.run_worker = False
        self.storedir = "~/.cache/task-maker/files"
        self.tempdir = "~/.cache/task-maker/temp"
        self.cache_size = 2048  # in MiB
        self._get_host_port()
        self._resolve_dir()

        # server group
        self.server_logfile = "/tmp/task-maker-server.log"
        self.server_pidfile = None  # type: Optional[str]
        self.server_address = None  # type: Optional[str]
        self.server_port = 7070
        self.server_verbose = False

        # worker group
        self.worker_logfile = "/tmp/task-maker-worker.log"
        self.worker_pidfile = None  # type: Optional[str]
        self.worker_keep_sandboxes = False
        self.worker_name = "local"
        self.worker_num_cores = None  # type: Optional[int]
        self.worker_port = 7070
        self.worker_address = "127.0.0.1"
        self.worker_pending_requests = None  # type: Optional[int]
        self.worker_verbose = False

        # execution group
        self.exclusive = False
        self.extra_time = 0.0
        self.copy_exe = False

        # IOI group
        self.detailed_checker = False

        # terry group
        self.arch = Arch.DEFAULT
        self.seed = None

        # statement group
        self.no_statement = False
        self.set = []

        # help group
        self.help_colors = False

        # bulk group
        self.contest_dir = os.getcwd()
        self.contest_yaml = None
        self.make_booklet = False
        # current index in bulk run and total number of bulk tasks
        self.bulk_number = None  # type: Optional[int]
        self.bulk_total = None  # type: Optional[int]

    def apply_args(self, args):
        """
        Apply all the options from Config.OPTIONS using the argparse's result
        """
        for group, options in Config.OPTIONS.items():
            for arg in options:
                self._apply_arg(arg, args)
        self._update_state()

    def apply_file(self):
        """
        Apply the configuration from the ~/.task-maker.toml file
        """
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
        self._update_state()

    def _apply_arg(self, name, args):
        value = getattr(args, name, None)
        if value is not None and value is not False:
            setattr(self, name, value)

    def _update_state(self):
        self._get_host_port()
        self._resolve_dir()
        self._get_contest_dir()

    def _get_host_port(self):
        server_addr = self.server.split(":")
        if len(server_addr) == 1:
            self.host, self.port = server_addr[0], 7071
        elif len(server_addr) == 2:
            self.host, self.port = server_addr[0], int(server_addr[1])
        else:
            raise ValueError("Invalid address for the server")

    def _resolve_dir(self):
        self.storedir = os.path.expanduser(self.storedir)
        self.tempdir = os.path.expanduser(self.tempdir)

    def _get_contest_dir(self):
        if self.contest_yaml:
            self.contest_dir = os.path.dirname(self.contest_yaml)

    def _get_value(self, group, item, value):
        if item in Config.CUSTOM_TYPES:
            try:
                return Config.CUSTOM_TYPES[item](value)
            except Exception:
                valid = [x.name.lower() for x in Config.CUSTOM_TYPES[item]]
                raise ValueError("Invalid config value at {}.{}, "
                                 "the valid values are: {}".format(
                                     group, item, ", ".join(valid)))
        return value

    def __repr__(self):
        return str(self.__dict__)
