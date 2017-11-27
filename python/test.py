#!/usr/bin/env python3
import bindings.core
import bindings.execution
import bindings.file_id

core = bindings.core.core()
ex = core.add_execution("test", "/usr/bin/bash", ["-c", "tree /var"])
print(core.run())
print(ex.stdout().contents(10000000))