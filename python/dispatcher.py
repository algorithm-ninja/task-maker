#!/usr/bin/env python3
from bindings.task_maker import core


class Dispatcher:
    def __init__(self):
        self._callbacks = dict()
        self._file_callbacks = dict()
        self._core = core.Core()
        core.set_callback(self._callback)

    def add_execution(self, description, executable, args, cb):
        execution = self._core.add_execution(description, executable, args)
        self._callbacks[execution.id()] = cb
        return execution

    def load_file(self, description, path, cb=None):
        file_id = self._core.load_file(description, path)
        if cb:
            self._file_callbacks[file_id.id()] = cb
        return file_id

    def run(self):
        return self._core.run()

    def _callback(self, task_status):
        if task_status.event == task_status.Event.BUSY:
            return True
        if task_status.event == task_status.Event.START:
            return True
        success = task_status.event == task_status.Event.SUCCESS
        message = None if success else task_status.message
        if task_status.type == FILE_LOAD:
            cause = task_status.file_info
            callback = self._file_callbacks.get(cause.id(), None)
        else:
            cause = task_status.execution_info
            callback = self._callbacks.get(cause.id(), None)
        if not callback:
            return success
        return callback(cause, success, message)
