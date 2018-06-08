#!/usr/bin/env python3

import argparse


def zsh_autocomplete(parser: argparse.ArgumentParser):
    """
    Generate a compdef autocompletion script, after generation you should place
    the file in a path in $fpath then relog
    """
    result = "#compdef task-maker\n"
    result += "\n"
    result += "# Add this file (_task_maker) to a directory in $fpath\n"
    result += "\n"
    result += "args=(\n"

    registered = set()

    def add_positional(option: argparse._StoreAction):
        nonlocal result
        line = "  '*:%s:{_files}'\n" % option.dest
        result += line

    def add_option(option: argparse._StoreAction):
        nonlocal result
        nonlocal registered

        params = strings = set(option.option_strings) - registered
        registered |= strings
        if not len(strings):
            return
        help = option.help.replace("'", "'\"'\"'")
        if isinstance(option, argparse._StoreAction):
            strings = [s + "=" if s.startswith("--") else s + "+"
                       for s in strings]
        line = "  '"
        if len(strings) > 1:
            line += "(%s)'{%s}'" % (
                " ".join(strings), ",".join(strings))
        else:
            line += "%s" % (list(strings)[0])
        line += "[%s]" % help

        if option.choices:
            line += ":%s type:(%s)" % (
                list(params)[0].replace("-", ""),
                " ".join(map(str, option.choices)))
        result += line + "'\n"

    for opt, value in parser._option_string_actions.items():
        add_option(value)
    for opt in parser._positionals._group_actions:
        add_positional(opt)

    result += ")\n"
    result += "\n"
    result += "_arguments -s -S $args\n"

    return result
