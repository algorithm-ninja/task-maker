#!/usr/bin/env python3

from enum import Enum
from typing import Callable
from typing import Dict  # pylint: disable=unused-import
from typing import List
from typing import Optional
from typing import Union
from bindings import Core
from bindings import Execution
from bindings import FileID
from python.ui import UI


class EventStatus(Enum):
    START = 0
    SUCCESS = 1
    FAILURE = 2


# pylint: disable=invalid-name

Event = Union[FileID, Execution]
DispatcherCallback = Callable[[Event, EventStatus], bool]

# pylint: enable=invalid-name


class Dispatcher:
    def __init__(self, ui: UI) -> None:
        self._callbacks = dict()  # type: Dict[int, DispatcherCallback]
        self._file_callbacks = dict()  # type: Dict[int, DispatcherCallback]
        self.core = Core()
        self.core.set_callback(self._callback)
        self._ui = ui

    def add_execution(self, description: str, executable: str, args: List[str],
                      callback: DispatcherCallback, exclusive: bool,
                      cache_mode: Execution.CachingMode) -> Execution:
        execution = self.core.add_execution(description, executable, args)
        if exclusive:
            execution.set_exclusive()
        execution.set_caching_mode(cache_mode)
        self._callbacks[execution.id()] = callback
        return execution

    def load_file(self,
                  description: str,
                  path: str,
                  callback: Optional[DispatcherCallback] = None) -> FileID:
        file_id = self.core.load_file(description, path)
        if callback:
            self._file_callbacks[file_id.id()] = callback
        return file_id

    def run(self) -> bool:
        return self.core.run()

    def _callback(self, task_status: Core.TaskStatus) -> bool:
        if task_status.event == task_status.Event.BUSY:
            return True
        if task_status.event == task_status.Event.FAILURE:
            self._ui.fatal_error(task_status.message)
            return False
        if task_status.type == task_status.Type.FILE_LOAD:
            cause = task_status.file_info  # type: Event
            callback = self._file_callbacks.get(cause.id(), None)
            success = True
        else:
            cause = task_status.execution_info
            callback = self._callbacks.get(cause.id(), None)
            success = task_status.execution_info.success()
        if not callback:
            return success
        if task_status.event == task_status.Event.START:
            event_status = EventStatus.START
        elif task_status.event == task_status.Event.SUCCESS:
            event_status = EventStatus.SUCCESS if success else EventStatus.FAILURE
        else:
            raise ValueError("Invalid task status")
        return callback(cause, event_status)
