#!/usr/bin/env python3
import os.path
from abc import ABC, abstractmethod
from enum import Enum
from task_maker.remote import ExecutionPool, Execution
from task_maker.task_maker_frontend import File, Result
from typing import Optional, List, Tuple


class StatementCompilationStatus(Enum):
    """
    Status of the compilation of a statement
    """
    WAITING = 0  # the compilation is pending
    COMPILING_DEPS = 1  # the dependencies are compiling
    COMPILED_DEPS = 2  # the dependencies are compiled
    COMPILING = 3  # the compilation has started
    DONE = 4  # the compilation completed successfully
    FAILED = 5  # the compilation failed


class StatementDepCompilationStatus(Enum):
    """
    Status of the execution of a statement dependency
    """
    WAITING = 0  # the execution is pending
    RUNNING = 1  # the execution is running
    DONE = 2  # the execution completed successfully
    FAILED = 3  # the execution failed


class StatementDepInfo:
    """
    Information of a statement dependency
    """

    def __init__(self, name: str, execution: Execution):
        self.name = name
        self.execution = execution
        self.result = None  # type: Optional[Result]
        self.status = StatementDepCompilationStatus.WAITING


class Statement(ABC):
    """
    Manage and compile statement files, all the executions populated after the
    compile method need the getResult method to be called.
    """

    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(self.path)
        self.compilation = None  # type: Execution
        self.compilation_result = None  # type: Result
        self.compilation_status = StatementCompilationStatus.WAITING
        self.pdf_file = None  # type: Optional[File]
        self.other_executions = []  # type: List[StatementDepInfo]

    @staticmethod
    @abstractmethod
    def compile_booklet(pool: ExecutionPool,
                        statements: List["Statement"],
                        language: Optional[str] = None
                        ) -> Tuple[Execution, File, List[StatementDepInfo]]:
        """
        Compile the booklet composed by the specified statements, the statements
        should be already compiled (the compile method already called)
        """
        pass

    @abstractmethod
    def compile(self, pool: ExecutionPool, language: Optional[str] = None):
        """
        Compile the statement file by adding some executions to the computation
        DAG.
        """
        pass
