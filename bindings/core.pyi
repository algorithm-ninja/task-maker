# pylint: disable=import-error
# pylint: disable=unused-argument
# pylint: disable=pointless-statement
# pylint: disable=no-self-use

from enum import Enum
from typing import Callable
from typing import List
from .execution import Execution
from .file_id import FileID


class Core:
    class TaskStatus:
        class Event(Enum):
            START = ...  # type: int
            SUCCESS = ...  # type: int
            BUSY = ...  # type: int
            FAILURE = ...  # type: int

        class Type(Enum):
            FILE_LOAD = ...  # type: int
            EXECUTION = ...  # type: int

        event = ...  # type: Event
        message = ...  # type: str
        type = ...  # type: Type
        file_info = ...  # type: FileID
        execution_info = ...  # type: Execution

    def __init__(self) -> None:
        ...

    def set_num_cores(self, num_cores: int) -> None:
        ...

    def set_temp_directory(self, directory: str) -> None:
        ...

    def set_store_directory(self, directory: str) -> None:
        ...

    def load_file(self, description: str, path: str) -> FileID:
        ...

    def add_execution(self, description: str, executable: str,
                      args: List[str]) -> Execution:
        ...

    def run(self) -> bool:
        ...

    def set_callback(self, callback: Callable[[TaskStatus], bool]) -> None:
        ...
