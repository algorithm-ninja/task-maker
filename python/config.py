#!/usr/bin/env python3

from typing import List

from task_maker.args import CacheMode, UIS, TaskFormat

# from task_maker.formats import Arch


class Config:
    def __init__(self, args):
        # generic group
        self.solutions = args.solutions  # type: List[str]
        self.task_dir = args.task_dir  # type: str
        self.max_depth = args.max_depth  # type: int
        self.ui = args.ui  # type: UIS
        self.cache = args.cache  # type: CacheMode
        # self.dry_run = args.dry_run  # type: bool
        self.clean = args.clean  # type: bool
        self.format = args.format  # type: TaskFormat

        # remote group
        self.server = args.server  # type: str
        # self.run_server = args.run_server  # type: bool
        # self.run_worker = args.run_worker  # type: bool
        server_addr = args.server.split(":")
        if len(server_addr) == 1:
            self.host, self.port = server_addr[0], 7071
        elif len(server_addr) == 2:
            self.host, self.port = server_addr[0], int(server_addr[1])
        else:
            raise ValueError("Invalid address for the server")

        # execution group
        # self.exclusive = args.exclusive  # type: bool
        # self.extra_time = args.extra_time  # type: float
        self.copy_exe = args.copy_exe  # type: # bool

        # terry group
        # self.arch = args.arch  # type: Arch
        # self.seed = args.seed  # type: int
