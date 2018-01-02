#!/usr/bin/env python3

import os.path
from proto.manager_pb2 import EvaluateTaskRequest
from proto.task_pb2 import Task, Subtask, TestCase, SourceFile, GraderInfo


def absolutize_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(os.getcwd(), path)


def absolutize_source_file(source_file: SourceFile) -> None:
    source_file.path = absolutize_path(source_file.path)
    for dependency in source_file.deps:
        dependency.path = absolutize_path(dependency.path)


def absolutize_testcase(testcase: TestCase) -> None:
    if testcase.HasField("generator"):
        absolutize_source_file(testcase.generator)
    if testcase.HasField("validator"):
        absolutize_source_file(testcase.validator)
    if testcase.input_file:
        testcase.input_file = absolutize_path(testcase.input_file)
    if testcase.output_file:
        testcase.output_file = absolutize_path(testcase.output_file)


def absolutize_subtask(subtask: Subtask) -> None:
    for testcase in subtask.testcases:
        absolutize_testcase(testcase)


def absolutize_grader_info(info: GraderInfo) -> None:
    for dependency in info.files:
        dependency.path = absolutize_path(dependency.path)


def absolutize_task(task: Task) -> None:
    for subtask in task.subtasks:
        absolutize_subtask(subtask)
    if task.HasField("official_solution"):
        absolutize_source_file(task.official_solution)
    for info in task.grader_info:
        absolutize_grader_info(info)
    if task.HasField("checker"):
        absolutize_source_file(task.checker)


def absolutize_request(request: EvaluateTaskRequest) -> None:
    absolutize_task(request.task)
    for solution in request.solutions:
        absolutize_source_file(solution)
    request.store_dir = absolutize_path(request.store_dir)
    request.temp_dir = absolutize_path(request.temp_dir)

    inputs = dict()
    for testcase, path in request.write_inputs_to.items():
        inputs[testcase] = absolutize_path(path)
    for testcase, path in inputs.items():
        request.write_inputs_to[testcase] = path

    outputs = dict()
    for testcase, path in request.write_outputs_to.items():
        outputs[testcase] = absolutize_path(path)
    for testcase, path in outputs.items():
        request.write_outputs_to[testcase] = path

    if request.write_checker_to:
        request.write_checker_to = absolutize_path(request.write_checker_to)
