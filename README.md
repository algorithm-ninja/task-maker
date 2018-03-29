# task-maker [![CircleCI](https://circleci.com/gh/algorithm-ninja/task-maker.svg?style=svg)](https://circleci.com/gh/algorithm-ninja/task-maker)

The new cmsMake!

## Usage

### Simple local usage
After installing task-maker, run `task_maker` in the task folder to compile
and run everything. Specifying no option all the caches are active, the next
executions will be very fast, actually doing only what's needed.

### Disable cache
If you really want to repeat the execution of something provide the `--cache`
option:
```bash
task_maker --cache=nothing
```

Possible values of `--cache` are: `all`, `generation` (do not regenerate
inputs/outputs if not needed), `nothing` (disable all the cache).

### Test only a subset of solutions
Sometimes you only want to test only some solutions, speeding up the
compilation and cleaning a bit the output:
```bash
task_maker sol1.cpp sol2.py
```

### Disable multithreading
If you want to be extra sure about the timings you can disable multithreading,
setting the number of core to 1:
```bash
task_maker --num-cores=1
```

### Using different task directory
By default the task in the current directory is executed, if you want to change
the task without `cd`-ing away:
```bash
task_maker --task-dir ~/tasks/poldo
```

### Extracting executable files
All the compiled files are kept in an internal folder but if you want to
use them, for example to debug a solution, passing `--copy-exe` all the
useful files are copied to the `bin/` folder inside the task directory.
```bash
task_maker --copy-exe
```

### Clean the task directory
If you want to clean everything, for example after the contest, simply run:
```bash
task_maker --clean
```

### Using a remote executor
One of the best feature of task-maker is the ability to execute a task remotely.
The setup is really simple, you need to start some programs: a server and
a group of workers. The server will accept connection from workers and clients,
a worker is the program that executes a command, a client is you!

First start a server:
```bash
bazel-bin/remote/server
```

Then start a worker in each machine, specifying the server to connect to:
```bash
bazel-bin/remote/worker -server server_ip:7070
```

If you want to see the logs from these two commands pass them `-logtostderr`.

To run the execution remotely just pass:
```bash
task_maker --evaluate-on server_ip:7070
```

Note that the TCP port 7070 is used, the connection has to be available,
stable and reliable. A local network is suggested but it should work also
via the Internet.

### Something went wrong
If something went wrong and you want to kill task-maker you have also to kill
the manager, a daemon spawned by task-maker.


## Compilation
For now the only installation method available is from source, there are some
compilation dependencies:
```
bazel python3-dev python3-setuptools python3-wheel g++
```

You need a compiler capable of compiling C++11.

This is also a python3 project, you need to have Python>=3.5 as default python
environment (running `python --version`), the easiest way to achieve this is
via virtualenv.
