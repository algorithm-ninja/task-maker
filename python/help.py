#!/usr/bin/env python3
import sys

from task_maker.config import Config
from task_maker.printer import StdoutPrinter


def help_colors():
    printer = StdoutPrinter()
    printer.text("Manual of the colors and abbreviations of task-maker\n")
    printer.text("\n")

    printer.text("During the execution process of a IOI task there are two\n")
    printer.text("main areas with colors: the generation and the evaluation\n")
    printer.text("\n")

    printer.blue("Generation of IOI task\n")
    printer.text("  .  ")
    printer.text("The generation has not started yet\n")
    printer.blue("  g  ", bold=True)
    printer.text("The generator of inputs is running\n")
    printer.text("  G  ")
    printer.text("The generator of inputs is done, waiting for validation\n")
    printer.blue("  v  ", bold=True)
    printer.text("The validator of inputs is running\n")
    printer.text("  V  ")
    printer.text("The validator of inputs is done, waiting for the solution\n")
    printer.blue("  s  ", bold=True)
    printer.text("The official solution is generating the output file\n")
    printer.green("  S  ")
    printer.text("The generation is finished\n")
    printer.red("  F  ")
    printer.text("The generation has failed\n")
    printer.text("\n")

    printer.blue("Evaluation of a IOI solution\n")
    printer.text("  .  ")
    printer.text("The evaluation has not started yet\n")
    printer.blue("  /  ", bold=True)
    printer.text("The solution is running\n")
    printer.text("  s  ")
    printer.text("The solution is done, waiting for the checker\n")
    printer.text("  /  ")
    printer.text("The checker is running\n")
    printer.text("  X  ")
    printer.text("The execution was skipped because a dependency failed\n")
    printer.green("  A  ", bold=True)
    printer.text("The solution outcome is accepted\n")
    printer.red("  W  ", bold=True)
    printer.text("The solution outcome is wrong\n")
    printer.yellow("  P  ", bold=True)
    printer.text("The solution outcome is partially correct\n")
    printer.red("  R  ", bold=True)
    printer.text("The solution is killed by runtime error (signal/return)\n")
    printer.red("  T  ", bold=True)
    printer.text("The solution got a time limit exceeded error\n")
    printer.red("  M  ", bold=True)
    printer.text("The solution got a memory limit exceeded error\n")
    printer.red("  F  ", bold=True)
    printer.text("The solution hasn't produced the output files\n")
    printer.bold("  I  ", bold=True)
    printer.text("An error occurred\n")
    printer.text("\n")
    printer.text("\n")

    printer.text("After an evaluation of a Terry task, a grid with a row for\n")
    printer.text("each solution is presented. The items in those rows are\n")
    printer.text("results of each testcase.\n")
    printer.text("\n")

    printer.blue("Evaluation of a Terry solution\n")
    printer.text("  m  ")
    printer.text("The output of that testcase is missing\n")
    printer.green("  c  ", bold=True)
    printer.text("The output of that testcase is correct\n")
    printer.red("  w  ", bold=True)
    printer.text("The output of that testcase is wrong\n")


def check_help(config: Config):
    if config.help_colors:
        help_colors()
        sys.exit(0)
