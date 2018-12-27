#!/usr/bin/env python3
import json
from task_maker.printer import Printer
from task_maker.task_maker_frontend import ResultStatus
from typing import Dict


class UIPrinter:
    """
    This class will manage the printing to the console, whether if it's text
    based or json
    """

    def __init__(self, printer: Printer, json: bool):
        self.printer = printer
        self.json = json

    def testcase_outcome(self, solution: str, testcase: int, subtask: int,
                         info: "TestcaseSolutionInfo"):
        if self.json:
            self._json(
                "testcase-outcome", "success", {
                    "name": solution,
                    "testcase": testcase,
                    "subtask": subtask,
                    "status": str(info.status).split(".")[-1],
                    "score": info.score,
                    "message": info.message
                })
        else:
            log = "Outcome of solution %s: score=%f message=%s" % (
                solution, info.score, info.message)
            self._print(log, "SUCCESS")

    def terry_solution_outcome(self, solution: str, info: "SolutionInfo"):
        if self.json:
            self._json(
                "solution-outcome", "success", {
                    "name":
                        solution,
                    "status":
                        str(info.status).split(".")[-1],
                    "score":
                        info.score,
                    "message":
                        info.message,
                    "testcases":
                        [str(s).split(".")[-1] for s in info.testcases_status]
                })
        else:
            log = "Outcome of solution %s: score=%f message=%s" % (
                solution, info.score, info.message)
            self._print(log, "SUCCESS")

    def warning(self, message: str):
        if self.json:
            self._json("warning", "warning", {"message": message})
        else:
            self._print("WARNING", "WARNING", data=message)

    def error(self, message: str):
        if self.json:
            self._json("error", "error", {"message": message})
        else:
            self._print("ERROR", "ERROR", data=message)

    def _print(self,
               prefix: str,
               state: str,
               data: str = None,
               cached: bool = False):
        if cached:
            prefix += " [cached]"
        if state == "WAITING":
            self.printer.text(prefix + "\n")
        elif state == "SKIPPED":
            self.printer.yellow(prefix + "\n")
        elif state == "START":
            self.printer.text(prefix + "\n")
        elif state == "SUCCESS":
            self.printer.green(prefix + "\n")
        elif state == "WARNING":
            self.printer.yellow(prefix + " " + str(data) + "\n")
        elif state == "FAIL" or state == "ERROR":
            self.printer.red(prefix + " " + str(data) + "\n")
        elif state == "STDERR":
            if data:
                self.printer.text(prefix + "\n" + str(data) + "\n")
        else:
            raise ValueError("Unknown state " + state)

    def _json(self, action: str, state: str, data: Dict, cached: bool = False):
        if isinstance(data, ResultStatus):
            data = str(data).split(".")[-1]
        data = {
            "action": action,
            "state": state,
            "data": data,
            "cached": cached
        }
        res = json.dumps(data)
        print(res, flush=True)

    def print(self, name: str, tag: str, state: str, data: Dict, cached: bool):
        if self.json:
            self._json(tag, state, data, cached)
        else:
            name = (name + " ").ljust(50) + state
            if cached:
                name += " [cached]"
            if state == "WAITING":
                self.printer.text(name + "\n")
            elif state == "SKIPPED":
                self.printer.yellow(name + "\n")
            elif state == "START":
                self.printer.text(name + "\n")
            elif state == "SUCCESS":
                self.printer.green(name + "\n")
            elif state == "WARNING":
                self.printer.yellow(name + " " + str(data) + "\n")
            elif state == "FAILURE" or state == "ERROR":
                self.printer.red(name + " " + str(data) + "\n")
            else:
                raise ValueError("Unknown state " + state)
