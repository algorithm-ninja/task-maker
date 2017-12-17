def smart_py_binary(name, srcs, deps, main = None):
  if main == None:
    main = name
  native.py_binary(
    name = name + "_py",
    srcs = srcs,
    deps = deps,
    main = main + ".py",
  )
  native.genrule(
      name = name + "_sh_",
      outs = [name + "_sh.sh"],
      srcs = [":" + name + "_py", ":" + main + ".py"],
      cmd = "mkdir -p $$(dirname $(OUTS)); echo \\#!/bin/bash > $(OUTS) && \
             echo \\$$\\(dirname \\$$0\\)/" + name +
              ".runfiles/oii_task_maker/tools/python_gateway.sh \
             \\$$\\(dirname \\$$0\\)/" + name +
              ".runfiles/oii_task_maker/$(location " + main + ".py) \
             \\\"\\$$@\\\" >> $(OUTS) \
             && chmod +x $(OUTS)"
  )
  native.sh_binary(
      name = name,
      srcs = [":" + name + "_sh.sh"],
      data = [":" + name + "_py"],
  )
