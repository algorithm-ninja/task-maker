#!/usr/bin/env python3
from bindings.task_maker import core
import tempfile


def callback(data):
    print(data.event, data.message, data.type)
    return data.event != core.Core.TaskStatus.Event.FAILURE


with tempfile.NamedTemporaryFile() as tmp:
    tmp.write(b"Lorem ipsum dolor sit amet.")
    tmp.seek(0)

    exec_core = core.Core()
    exec_core.set_callback(callback)
    f = exec_core.load_file("tmp file", tmp.name)
    ex = exec_core.add_execution("test", "/bin/cat", ["foobar"])
    ex.input("foobar", f)
    assert exec_core.run()
    assert ex.stdout().contents(100) == "Lorem ipsum dolor sit amet."
    assert ex.stderr().contents(100) == ""
