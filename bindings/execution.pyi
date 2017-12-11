# pylint: disable=import-error
# pylint: disable=unused-argument
# pylint: disable=pointless-statement
# pylint: disable=no-self-use
# pylint: disable=invalid-name

from enum import Enum
from typing import Optional
from .file_id import FileID


class Execution:
    class CachingMode(Enum):
        ALWAYS = ...  # type: int
        SAME_EXECUTOR = ...  # type: int
        NEVER = ...  # type: int

    def description(self) -> str:
        ...

    def id(self) -> int:
        ...

    def stdin(self, input_file: FileID) -> None:
        ...

    def input(self, name: str, input_file: FileID) -> None:
        ...

    def stdout(self) -> FileID:
        ...

    def stderr(self) -> FileID:
        ...

    def output(self, name: str, description: Optional[str] = None) -> FileID:
        ...

    def cpu_limit(self, limit: float) -> None:
        ...

    def wall_limit(self, limit: float) -> None:
        ...

    def memory_limit(self, kb: int) -> None:
        ...

    def process_limit(self, limit: int) -> None:
        ...

    def file_limit(self, limit: int) -> None:
        ...

    def file_size_limit(self, kb: int) -> None:
        ...

    def memory_lock_limit(self, limit: int) -> None:
        ...

    def stack_limit(self, limit: int) -> None:
        ...

    def set_exclusive(self) -> None:
        ...

    def set_caching_mode(self, caching_mode: CachingMode) -> None:
        ...

    def status_code(self) -> int:
        ...

    def signal(self) -> int:
        ...

    def success(self) -> bool:
        ...

    def cpu_time(self) -> float:
        ...

    def sys_time(self) -> float:
        ...

    def wall_time(self) -> float:
        ...

    def memory(self) -> int:
        ...
