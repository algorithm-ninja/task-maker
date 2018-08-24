#!/usr/bin/env python3

# enable discovery of capnp folder and installed venv
from task_maker.config import Config
from task_maker.syspath_patch import patch_sys_path
patch_sys_path()

import os.path

from task_maker.task_maker_frontend import Frontend

# from task_maker.formats import ioi_format, terry_format, tm_format
from task_maker.formats import ioi_format
from task_maker.args import get_parser
from task_maker.detect_format import find_task_dir

# from task_maker.manager import get_manager, became_manager, became_server, \
#     became_worker


# def manager_clean(args):
#     request = CleanTaskRequest()
#     request.store_dir = os.path.abspath(args.store_dir)
#     request.temp_dir = os.path.abspath(args.temp_dir)
#     manager = get_manager(args)
#     manager.CleanTask(request)
#
#
def ioi_format_clean():
    ioi_format.clean()


# def tm_format_clean(args):
#     tm_format.clean()
#     manager_clean(args)
#
#
# def terry_format_clean(args):
#     terry_format.clean()
#     manager_clean(args)

#
# def quit_manager(args, force):
#     request = ShutdownRequest()
#     request.force = force
#     manager = get_manager(args)
#     manager.Shutdown(request)


def main() -> None:
    config = Config(get_parser().parse_args())

    # if args.run_manager is not None:
    #     became_manager(args)
    # if args.run_server is not None:
    #     became_server(args)
    # if args.run_worker is not None:
    #     became_worker(args)
    #
    # if args.kill_manager:
    #     quit_manager(args, True)
    # if args.quit_manager:
    #     quit_manager(args, False)
    # if args.kill_manager or args.quit_manager:
    #     return
    #
    task_dir, format = find_task_dir(config.task_dir, config.max_depth)
    if not format:
        raise ValueError(
            "Cannot detect format! It's probable that the task is ill-formed")
    # TODO move this check in find_task_dir in order to have compatible formats
    if config.format is not None and format != config.format:
        raise ValueError(
            "Detected format mismatch the required one: %s" % format)

    os.chdir(task_dir)

    if config.clean:
        if format == "ioi":
            ioi_format_clean()
        # elif format == "tm":
        #     tm_format_clean(args)
        # elif format == "terry":
        #     terry_format_clean(args)
        else:
            raise ValueError("Format %s not supported" % format)
        return

    frontend = Frontend(config.host, config.port)

    if format == "ioi":
        task, solutions = ioi_format.get_request(config)
        ioi_format.evaluate_task(frontend, task, solutions, config.ui)
    # elif format == "tm":
    #     request = tm_format.get_request(args)
    #     solutions = [os.path.basename(sol.path) for sol in request.solutions]
    # elif format == "terry":
    #     request = terry_format.get_request(args)
    #     solutions = [
    #         os.path.basename(sol.solution.path) for sol in request.solutions
    #     ]
    # else:
    #     raise ValueError("Format %s not supported" % format)

    # import jsonpickle
    # import json
    # print(json.dumps(json.loads(jsonpickle.dumps(task)), indent=4))

    #
    # def stop_server(signum: int, _: Any) -> None:
    #     if eval_id:
    #         ui.stop("Waiting the manager to complete the last job")
    #         manager.Stop(StopRequest(evaluation_id=eval_id))
    #     ui.fatal_error("Aborted with sig%d" % signum)
    #
    # signal.signal(signal.SIGINT, stop_server)
    # signal.signal(signal.SIGTERM, stop_server)


if __name__ == '__main__':
    main()
