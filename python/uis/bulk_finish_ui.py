#!/usr/bin/env python3
from typing import List
import shutil

from task_maker.printer import StdoutPrinter
from task_maker.config import Config
from task_maker.uis import FinishUI, UIInterface
from task_maker.uis.ioi import IOIUIInterface
from task_maker.uis.ioi_finish_ui import IOIFinishUI
from task_maker.uis.terry import TerryUIInterface
from task_maker.uis.terry_finish_ui import TerryFinishUI


def _horizontal_line():
    size = shutil.get_terminal_size((80, 20))
    print("\u2014" * size.columns)


class BulkFinishUI(FinishUI):
    def __init__(self, config: Config):
        super().__init__(config, None)
        self.interfaces = list()  # type: List[UIInterface]
        self.uis = list()  # type: List[FinishUI]
        self.errors = list()  # type: List[str]

    def add_interface(self, interface: UIInterface):
        if isinstance(interface, IOIUIInterface):
            ui = IOIFinishUI(self.config, interface)
        elif isinstance(interface, TerryUIInterface):
            ui = TerryFinishUI(self.config, interface)
        else:
            self.add_error("Unknown interface format: " + interface.task.name)
            return
        self.interfaces.append(interface)
        self.uis.append(ui)

    def add_error(self, message: str):
        self.errors.append(message)

    def print(self):
        for ui in self.uis:
            _horizontal_line()
            ui.print()
            print("\n")
        self.print_summary()
        self.print_final_messages()

    def print_summary(self):
        printer = StdoutPrinter()
        printer.blue("Bulk summary:\n", bold=True)
        for i, ui in enumerate(self.uis):
            if i > 0:
                print()
                _horizontal_line()
            printer.bold("Task: " + ui.interface.task.name + "\n\n")
            ui.print_summary()
            ui.print_final_messages()

    def print_final_messages(self):
        if self.errors:
            printer = StdoutPrinter()
            print()
            _horizontal_line()
            printer.red("Bulk errors:\n", bold=True)
            for error in self.errors:
                self.printer.text("- " + error + "\n")
