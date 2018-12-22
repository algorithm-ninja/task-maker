#!/usr/bin/env python3
import shutil
from task_maker.config import Config
from task_maker.printer import StdoutPrinter
from task_maker.uis import FinishUI, UIInterface
from task_maker.uis.ioi import IOIUIInterface
from task_maker.uis.ioi_finish_ui import IOIFinishUI
from task_maker.uis.terry import TerryUIInterface
from task_maker.uis.terry_finish_ui import TerryFinishUI
from typing import List


def _horizontal_line():
    """
    Print an horizontal line in the center of the screen
    """
    size = shutil.get_terminal_size((80, 20))
    print("\u2014" * size.columns)


class BulkFinishUI(FinishUI):
    """
    Finish UI for bulk makes, this will take many UIInterfaces
    """
    def __init__(self, config: Config):
        super().__init__(config, None)
        self.interfaces = list()  # type: List[UIInterface]
        self.uis = list()  # type: List[FinishUI]
        self.errors = list()  # type: List[str]

    def add_interface(self, interface: UIInterface):
        """
        Add a new interface to track and later print the final result
        """
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
        """
        Add an error to the errors list
        """
        self.errors.append(message)

    def print(self):
        """
        Print the final result of all the interfaces
        """
        for ui in self.uis:
            _horizontal_line()
            ui.print()
            print("\n")
        self.print_summary()
        self.print_final_messages()

    def print_summary(self):
        """
        Print the summary of the executions of each task close together
        """
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
        """
        Print the list of bulk errors
        """
        if self.errors:
            printer = StdoutPrinter()
            print()
            _horizontal_line()
            printer.red("Bulk errors:\n", bold=True)
            for error in self.errors:
                self.printer.text("- " + error + "\n")
