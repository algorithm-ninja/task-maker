#!/usr/bin/env python3

from sys import argv, exit, stderr
from parser import Parser
import json

if len(argv) != 3:
    print("Usage: %s input_file output_file" % argv[0], file=stderr)
    exit(1)

task_input = open(argv[1], "r")
human_output = open(argv[2], "r")

T = int(task_input.readlines()[0])


def evaluate(num, stream):
    N = stream.int()
    return 1.0 if num == N else 0.0


parser = Parser(
    evaluate,
    T,
    human_output,
    int_max_len=20,
    str_max_len=50,
    strict_spaces=False)

print(json.dumps(parser.run()))
