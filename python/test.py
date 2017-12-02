#!/usr/bin/env python3
from bindings.task_maker import core
from bindings.task_maker import file_id
from bindings.task_maker import execution
import tempfile

with tempfile.NamedTemporaryFile() as tmp:
    tmp.write(b"Lorem ipsum dolor sit amet.")
    tmp.seek(0)

    exec_core = core.core()
    f = exec_core.load_file("tmp file", tmp.name)
    ex = exec_core.add_execution("test", "/bin/cat", ["foobar"])
    ex.input("foobar", f)
    assert exec_core.run()
    assert ex.stdout().contents(100) == "Lorem ipsum dolor sit amet."
    assert ex.stderr().contents(100) == ""
