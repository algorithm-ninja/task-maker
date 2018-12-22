#!/usr/bin/env python3
import json
from task_maker.printer import Printer
from task_maker.task_maker_frontend import ResultStatus


class UIPrinter:
    """
    This class will manage the printing to the console, whether if it's text
    based or json
    """

    def __init__(self, printer: Printer, json: bool):
        self.printer = printer
        self.json = json

    def compilation_non_solution(self,
                                 name: str,
                                 state: str,
                                 data: str = None,
                                 cached: bool = False):
        if self.json:
            self._json("compilation-non-solution", state, {"name": name}, data,
                       cached)
        else:
            log = ("Compilation of non-solution %s " % name).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def compilation_solution(self,
                             name: str,
                             state: str,
                             data: str = None,
                             cached: bool = False):
        if self.json:
            self._json("compilation-solution", state, {"name": name}, data,
                       cached)
        else:
            log = ("Compilation of solution %s " % name).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def generation(self,
                   testcase: int,
                   subtask: int,
                   state: str,
                   data: str = None,
                   cached: bool = False):
        if self.json:
            self._json("generation", state, {
                "testcase": testcase,
                "subtask": subtask
            }, data, cached)
        else:
            log = ("Generation of input %d of subtask %d " %
                   (testcase, subtask)).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def terry_generation(self,
                         solution: str,
                         seed: int,
                         state: str,
                         data: str = None,
                         cached: bool = False):
        if self.json:
            self._json("generation", state, {
                "solution": solution,
                "seed": seed
            }, data, cached)
        else:
            log = ("Generation of input for %s with seed %d " %
                   (solution, seed)).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def validation(self,
                   testcase: int,
                   subtask: int,
                   state: str,
                   data: str = None,
                   cached: bool = False):
        if self.json:
            self._json("validation", state, {
                "testcase": testcase,
                "subtask": subtask
            }, data, cached)
        else:
            log = ("Validation of input %d of subtask %d " %
                   (testcase, subtask)).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def terry_validation(self,
                         solution: str,
                         state: str,
                         data: str = None,
                         cached: bool = False):
        if self.json:
            self._json("validation", state, {"solution": solution}, data,
                       cached)
        else:
            log = ("Validation of input for %s " % solution).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def solving(self,
                testcase: int,
                subtask: int,
                state: str,
                data: str = None,
                cached: bool = False):
        if self.json:
            self._json("solving", state, {
                "testcase": testcase,
                "subtask": subtask
            }, data, cached)
        else:
            log = ("Generation of output %d of subtask %d " %
                   (testcase, subtask)).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def evaluate(self,
                 solution: str,
                 num: int,
                 num_processes: int,
                 testcase: int,
                 subtask: int,
                 state: str,
                 data: str = None,
                 cached: bool = False):
        if self.json:
            self._json(
                "evaluate", state, {
                    "solution": solution,
                    "num": num,
                    "num_processes": num_processes,
                    "testcase": testcase,
                    "subtask": subtask
                }, data, cached)
        else:
            if num_processes == 1:
                log = "Evaluate %s on case %d of subtask %d " % (
                    solution, testcase, subtask)
            else:
                log = "Evaluate %s (%d/%d) on case %d of subtask %d " % (
                    solution, num + 1, num_processes, testcase, subtask)
            log = log.ljust(50) + state
            self._print(log, state, data=data, cached=cached)

    def terry_evaluate(self,
                       solution: str,
                       state: str,
                       data: str = None,
                       cached: bool = False):
        if self.json:
            self._json("evaluate", state, {"solution": solution}, data, cached)
        else:
            log = ("Evaluate solution %s " % solution).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def checking(self,
                 solution: str,
                 testcase: int,
                 subtask: int,
                 state: str,
                 data: str = None,
                 cached: bool = False):
        if self.json:
            self._json("checking", state, {
                "solution": solution,
                "testcase": testcase,
                "subtask": subtask
            }, data, cached)
        else:
            log = ("Checking solution %s on case %d of subtask %d " %
                   (solution, testcase, subtask)).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def terry_checking(self,
                       solution: str,
                       state: str,
                       data: str = None,
                       cached: bool = False):
        if self.json:
            self._json("checking", state, {"solution": solution}, data, cached)
        else:
            log = ("Checking solution %s " % solution).ljust(50)
            log += state
            self._print(log, state, data=data, cached=cached)

    def testcase_outcome(self, solution: str, testcase: int, subtask: int,
                         info: "TestcaseSolutionInfo"):
        if self.json:
            self._json(
                "testcase-outcome", "success", {
                    "solution": solution,
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
                    "solution":
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

    def _json(self,
              action: str,
              state: str,
              extra: dict,
              data: str = None,
              cached: bool = False):
        if isinstance(data, ResultStatus):
            data = str(data).split(".")[-1]
        data = {
            "action": action,
            "state": state,
            "data": data,
            "cached": cached
        }
        for k, v in extra.items():
            data[k] = v
        res = json.dumps(data)
        print(res, flush=True)
