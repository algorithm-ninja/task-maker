#!/usr/bin/env python3
import bindings.core
import bindings.execution
import bindings.file_id
import tempfile

with tempfile.NamedTemporaryFile() as tmp:
    tmp.write(b"Lorem ipsum dolor sit amet.")
    tmp.seek(0)

    core = bindings.core.core()
    f = core.load_file("tmp file", tmp.name)
    ex = core.add_execution("test", "/bin/cat", ["foobar"])
    ex.input("foobar", f)
    assert core.run()
    assert ex.stdout().contents(100) == "Lorem ipsum dolor sit amet."
    assert ex.stderr().contents(100) == ""
