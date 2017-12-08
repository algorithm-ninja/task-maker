#!/usr/bin/env python3

from typing import Callable
from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional
from typing import Union
from bindings import Core
from bindings import Execution
from bindings import FileID

# pylint: disable=invalid-name

Event = Union[FileID, Execution]
DispatcherCallback = Callable[[Event, bool, Optional[str]], bool]

# pylint: enable=invalid-name


class Dispatcher:
    def __init__(self) -> None:
        self._callbacks = dict()  # type: Dict[int, DispatcherCallback]
        self._file_callbacks = dict()  # type: Dict[int, DispatcherCallback]
        self._core = Core()
        self._core.set_callback(self._callback)

    def add_execution(self, description: str, executable: str, args: List[str],
                      callback: DispatcherCallback) -> Execution:
        execution = self._core.add_execution(description, executable, args)
        self._callbacks[execution.id()] = callback
        return execution

    def load_file(self,
                  description: str,
                  path: str,
                  callback: Optional[DispatcherCallback] = None) -> FileID:
        file_id = self._core.load_file(description, path)
        if callback:
            self._file_callbacks[file_id.id()] = callback
        return file_id

    def run(self) -> bool:
        return self._core.run()

    def _callback(self, task_status: Core.TaskStatus) -> bool:
        if task_status.event == task_status.Event.BUSY:
            return True
        if task_status.event == task_status.Event.START:
            return True
        success = task_status.event == task_status.Event.SUCCESS
        message = None if success else task_status.message
        if task_status.type == task_status.Type.FILE_LOAD:
            cause = task_status.file_info  # type: Event
            callback = self._file_callbacks.get(cause.id(), None)
        else:
            cause = task_status.execution_info
            callback = self._callbacks.get(cause.id(), None)
        if not callback:
            return success
        return callback(cause, success, message)
