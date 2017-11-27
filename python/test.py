#!/usr/bin/env python3
import bindings.core
import bindings.execution
import bindings.file_id

with open("foo", 'w') as f:
    f.write("bar")

core = bindings.core.core()
f = core.load_file("foo", "foo")
ex = core.add_execution("test", "/bin/cat", ["foobar"])
ex.input("foobar", f)
assert (core.run())
assert (ex.stdout().contents(100) == 'bar')
