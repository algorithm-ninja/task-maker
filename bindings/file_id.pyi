# pylint: disable=unused-argument
# pylint: disable=pointless-statement
# pylint: disable=no-self-use
# pylint: disable=invalid-name


class FileID:
    def description(self) -> str:
        ...

    def id(self) -> int:
        ...

    def write_to(self, path: str) -> None:
        ...

    def contents(self, size_limit: int) -> str:
        ...
