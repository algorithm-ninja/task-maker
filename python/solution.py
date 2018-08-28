#!/usr/bin/env python3

from abc import ABC, abstractmethod
from task_maker.args import CacheMode
from task_maker.config import Config
from task_maker.formats import Task
from task_maker.source_file import SourceFile
from task_maker.task_maker_frontend import File, Execution, Frontend, Resources, \
    Fifo
from typing import Optional, List, Tuple


class Solution(ABC):
    def __init__(self, solution: SourceFile, task: Task, config: Config):
        self.solution = solution
        self.task = task
        self.config = config

    @abstractmethod
    def evaluate(
            self, frontend: Frontend, testcase: int, subtask: int, input: File,
            validation: Optional[File],
            correct_output: Optional[File]) -> (List[Execution], Execution):
        """
        Evaluate this solution against this input/output.
        Assuming self.solution is already prepared
        :param frontend: the frontend
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
    def __init__(self, solution: SourceFile, task: Task, config: Config,
                 checker: SourceFile):
        super().__init__(solution, task, config)
        self.checker = checker

    def evaluate(
            self, frontend: Frontend, testcase: int, subtask: int, input: File,
            validation: Optional[File],
            correct_output: Optional[File]) -> (List[Execution], Execution):
        eval = self.solution.execute(
            frontend,
            "Evaluation of %s on testcase %d" % (self.solution.name, testcase),
            [])
        if self.config.cache != CacheMode.ALL:
            eval.disableCache()
        limits = Resources()
        limits.cpu_time = self.task.time_limit
        limits.wall_time = self.task.time_limit * 1.5
        limits.memory = self.task.memory_limit_kb
        eval.setLimits(limits)
        if validation:
            eval.addInput("tm_wait_validation", validation)
        if self.task.input_file:
            eval.addInput(self.task.input_file, input)
        else:
            eval.setStdin(input)
        if self.task.output_file:
            output = eval.output(self.task.output_file, False)
        else:
            output = eval.stdout(False)
        if self.config.exclusive:
            eval.makeExclusive()
        if self.config.extra_time:
            eval.setExtraTime(self.config.extra_time)

        if self.checker:
            check = self.checker.execute(
                frontend, "Checking solution %s for testcase %d" %
                (self.solution.name, testcase),
                ["input", "output", "contestant_output"])
            check.addInput("input", input)
        else:
            check = frontend.addExecution(
                "Checking solution %s for testcase %d" % (self.solution.name,
                                                          testcase))
            check.setExecutablePath("diff")
            check.setArgs(["-w", "output", "contestant_output"])
            check.addInput("output", correct_output)
            check.addInput("contestant_output", output)
        if self.config.cache != CacheMode.ALL:
            check.disableCache()
        limits = Resources()
        limits.cpu_time = self.task.time_limit * 2
        limits.wall_time = self.task.time_limit * 1.5 * 2
        limits.memory = self.task.memory_limit_kb * 2
        check.setLimits(limits)

        return [eval], check


class CommunicationSolution(Solution):
    def __init__(self, solution: SourceFile, task: Task, config: Config,
                 manager: SourceFile, num_processes: int):
        super().__init__(solution, task, config)
        self.manager = manager
        self.num_processes = num_processes

    def evaluate(
            self, frontend: Frontend, testcase: int, subtask: int, input: File,
            validation: Optional[File],
            correct_output: Optional[File]) -> (List[Execution], Execution):
        group = frontend.addExecutionGroup(
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
        for p_in, p_out, p_in_name, p_out_name in zip(
                pipes_m_2_sol, pipes_sol_2_m, pipes_m_2_sol_names,
                pipes_sol_2_m_names):
            exec = self.solution.execute(
                frontend, "Evaluation of %s (process %d) on testcase %d" %
                (self.solution.name, p, testcase),
                [p_out_name, p_in_name, str(p)], group)
            limits = Resources()
            limits.cpu_time = self.task.time_limit
            limits.wall_time = self.task.time_limit * 1.5
            limits.memory = self.task.memory_limit_kb
            exec.setLimits(limits)
            if validation:
                exec.addInput("tm_wait_validation", validation)
            if self.config.extra_time:
                exec.setExtraTime(self.config.extra_time)
            exec.addFifo(p_in_name, p_in)
            exec.addFifo(p_out_name, p_out)

            executions.append(exec)

        args = []
        for p_in_name, p_out_name in zip(pipes_sol_2_m_names,
                                         pipes_m_2_sol_names):
            args += [p_out_name, p_in_name]
        manager = self.manager.execute(
            frontend, "Evaluation of %s (manager process) on testcase %d" %
            (self.solution.name, testcase), args, group)
        limits = Resources()
        limits.cpu_time = self.task.time_limit * self.num_processes
        limits.wall_time = limits.cpu_time * 1.5
        manager.setLimits(limits)
        for p_in, p_out, p_in_name, p_out_name in zip(
                pipes_m_2_sol, pipes_sol_2_m, pipes_m_2_sol_names,
                pipes_sol_2_m_names):
            manager.addFifo(p_in_name, p_in)
            manager.addFifo(p_out_name, p_out)
        if self.task.input_file:
            manager.addInput(self.task.input_file, input)
        else:
            manager.setStdin(input)

        if self.config.exclusive:
            manager.makeExclusive()  # this will be propagated to the group
        if self.config.cache != CacheMode.ALL:
            manager.disableCache()  # this will be propagated to the group

        return executions, manager
