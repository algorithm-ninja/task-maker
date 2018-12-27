#!/usr/bin/env python3

from abc import ABC, abstractmethod
from task_maker.args import CacheMode
from task_maker.config import Config
from task_maker.formats import IOITask
from task_maker.remote import Execution, ExecutionPool
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import File, Resources, Fifo
from typing import Optional, List, Dict


def get_checker_execution(pool: ExecutionPool,
                          task: IOITask,
                          name: str,
                          subtask: int,
                          testcase: int,
                          checker: Optional[SourceFile],
                          input: Optional[File],
                          output: File,
                          correct_output: File,
                          message: str,
                          extra_data: Dict = None) -> Execution:
    """
    Build the execution of the checker, it could be a custom checker or the
    default diff one.
    """
    if not extra_data:
        extra_data = dict()
    inputs = dict()
    if checker:
        checker.prepare(pool)
        cmd = checker
        args = ["input", "output", "contestant_output"]
        inputs["input"] = input
    else:
        cmd = "diff"
        args = ["-w", "output", "contestant_output"]
    inputs["output"] = correct_output
    inputs["contestant_output"] = output
    limits = Resources()
    limits.cpu_time = task.time_limit * 2
    limits.wall_time = task.time_limit * 1.5 * 2
    limits.memory = task.memory_limit_kb * 2
    return Execution(
        message,
        pool,
        cmd,
        args,
        "checking", {
            "name": name,
            "subtask": subtask,
            "testcase": testcase,
            **extra_data
        },
        cache_on=[CacheMode.ALL],
        limits=limits,
        inputs=inputs,
        store_stdout=True,
        store_stderr=True)


class Solution(ABC):
    """
    Abstract class that manages a solution.
    """

    def __init__(self, solution: SourceFile, task: IOITask, config: Config):
        self.solution = solution
        self.task = task
        self.config = config

    @abstractmethod
    def evaluate(self, testcase: int, subtask: int, input: File,
                 validation: Optional[File], correct_output: Optional[File]
                 ) -> (List[Execution], Execution):
        """
        Evaluate this solution against this input/output.
        Assuming self.solution is already prepared
        :param testcase: number of the testcase
        :param subtask: number of the subtask
        :param input: input file
        :param validation: validation stdout, useful to evaluate only after
            valiation
        :param correct_output: output file
        :return: a list of the "evaluating" executions with the checker
            execution
        """
        pass


class BatchSolution(Solution):
    """
    The task type is Batch, the evaluation consists in executing the solution
    giving the input, taking the output and checking it.
    """

    def __init__(self, solution: SourceFile, task: IOITask, config: Config,
                 checker: SourceFile):
        super().__init__(solution, task, config)
        self.checker = checker

    def evaluate(self, testcase: int, subtask: int, input: File,
                 validation: Optional[File], correct_output: Optional[File]
                 ) -> (List[Execution], Execution):
        limits = Resources()
        limits.cpu_time = self.task.time_limit
        limits.wall_time = self.task.time_limit * 1.5
        limits.memory = self.task.memory_limit_kb
        inputs = dict()
        if validation:
            inputs["tm_wait_validation"] = validation
        if self.task.input_file:
            inputs[self.task.input_file] = input
            stdin = None
        else:
            stdin = input
        outputs = []
        if self.task.output_file:
            outputs.append(self.task.output_file)
        eval = Execution(
            "Evaluation of %s on testcase %d" % (self.solution.name, testcase),
            self.solution.pool,
            self.solution, [],
            "evaluation", {
                "name": self.solution.name,
                "subtask": subtask,
                "testcase": testcase
            },
            cache_on=[CacheMode.ALL],
            extra_time=self.config.extra_time,
            limits=limits,
            can_exclusive=True,
            stdin=stdin,
            inputs=inputs,
            outputs=outputs)
        if self.task.output_file:
            output = eval.output(self.task.output_file)
        else:
            output = eval.stdout

        check = get_checker_execution(
            self.solution.pool, self.task, self.solution.name, subtask,
            testcase, self.checker, input, output, correct_output,
            "Checking solution %s for testcase %d" % (self.solution.name,
                                                      testcase))

        return [eval], check


class CommunicationSolution(Solution):
    """
    The task type is Communication, a number of solutions and a manager are
    spawned, giving to them an input file.
    """

    def __init__(self, solution: SourceFile, task: IOITask, config: Config,
                 manager: SourceFile, num_processes: int):
        super().__init__(solution, task, config)
        self.manager = manager
        self.num_processes = num_processes

    def evaluate(self, testcase: int, subtask: int, input: File,
                 validation: Optional[File], correct_output: Optional[File]
                 ) -> (List[Execution], Execution):
        group = self.solution.pool.frontend.addExecutionGroup(
            "Evaluation of %s on testcase %d" % (self.solution.name, testcase))

        pipes_m_2_sol = []  # type: List[Fifo]
        pipes_sol_2_m = []  # type: List[Fifo]
        pipes_m_2_sol_names = []  # type: List[str]
        pipes_sol_2_m_names = []  # type: List[str]
        for p in range(self.num_processes):
            pipes_m_2_sol.append(group.createFifo())
            pipes_sol_2_m.append(group.createFifo())
            pipes_m_2_sol_names.append("pipe_m_2_sol%d" % p)
            pipes_sol_2_m_names.append("pipe_sol%d_2_m" % p)

        executions = []
        for p, (p_in, p_out, p_in_name, p_out_name) in enumerate(
                zip(pipes_m_2_sol, pipes_sol_2_m, pipes_m_2_sol_names,
                    pipes_sol_2_m_names)):
            limits = Resources()
            limits.cpu_time = self.task.time_limit
            limits.wall_time = self.task.time_limit * 1.5
            limits.memory = self.task.memory_limit_kb
            inputs = dict()
            if validation:
                inputs["tm_wait_validation"] = validation
            inputs[p_in_name] = p_in
            inputs[p_out_name] = p_out
            exec = Execution(
                "Evaluation of %s (process %d) on testcase %d" %
                (self.solution.name, p, testcase),
                self.solution.pool,
                self.solution,
                [p_out_name, p_in_name, str(p)],
                "evaluation", {
                    "name": self.solution.name,
                    "process": p + 1,
                    "num_processes": self.num_processes,
                    "subtask": subtask,
                    "testcase": testcase
                },
                group=group,
                extra_time=self.config.extra_time,
                limits=limits,
                inputs=inputs)
            executions.append(exec)

        args = []
        for p_in_name, p_out_name in zip(pipes_sol_2_m_names,
                                         pipes_m_2_sol_names):
            args += [p_out_name, p_in_name]

        limits = Resources()
        limits.cpu_time = self.task.time_limit * self.num_processes
        limits.wall_time = limits.cpu_time * 1.5
        inputs = dict()
        for p_in, p_out, p_in_name, p_out_name in zip(
                pipes_m_2_sol, pipes_sol_2_m, pipes_m_2_sol_names,
                pipes_sol_2_m_names):
            inputs[p_in_name] = p_in
            inputs[p_out_name] = p_out
        if self.task.input_file:
            inputs[self.task.input_file] = input
            stdin = None
        else:
            stdin = input
        outputs = []
        if self.task.output_file:
            outputs.append(self.task.output_file)

        manager = Execution(
            "Evaluation of %s (manager process) on testcase %d" %
            (self.solution.name, testcase),
            self.manager.pool,
            self.manager,
            args,
            "evaluation", {
                "name": self.solution.name,
                "process": 0,
                "num_processes": self.num_processes,
                "subtask": subtask,
                "testcase": testcase
            },
            group=group,
            limits=limits,
            inputs=inputs,
            outputs=outputs,
            stdin=stdin,
            can_exclusive=True,
            cache_on=[CacheMode.ALL],
            store_stdout=True,
            store_stderr=True)

        return executions, manager
