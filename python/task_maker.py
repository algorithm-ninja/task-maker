#!/usr/bin/env python3

import os

import grpc
from proto import manager_pb2_grpc
from proto.manager_pb2 import GetEventsRequest

from python.absolutize import absolutize_request
from python.args import get_parser
from python.italian_format import get_request


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    os.chdir(args.task_dir)

    if args.clean:
        # TODO: implement the clean process on the manager
        return

    channel = grpc.insecure_channel(args.manager_addr)
    manager = manager_pb2_grpc.TaskMakerManagerStub(channel)

    request = get_request(args)
    absolutize_request(request)

    response = manager.EvaluateTask(request)
    for event in manager.GetEvents(GetEventsRequest(evaluation_id=response.id)):
        print("event:", event)


if __name__ == '__main__':
    main()
