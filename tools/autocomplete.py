#!/usr/bin/env python3

import argparse
import os.path


def zsh_autocomplete(parser: argparse.ArgumentParser, command: str):
    """
    Generate a compdef autocompletion script, after generation you should place
    the file in a path in $fpath then relog
    """
    result = "#compdef %s\n" % command
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
        help = option.help.replace("'", "'\"'\"'")\
                          .replace("[", "\\[")\
                          .replace("]", "\\]")
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


def get_parser(*args, **kwargs):
    args_file = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "..", "python", "args.py")
    globals = dict()
    exec(open(args_file).read(), globals)
    return globals["get_parser"](*args, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contest-maker", action="store_true",
                        help="Generate the completion for contest-maker")
    parser.add_argument("-o", "--output",
                        help="Save the file to the specified path")
    parser.add_argument("shell", choices=["zsh", "bash"],
                        help="Completion for which shell")
    args = parser.parse_args()

    the_parser = get_parser(args.contest_maker)
    command = "contest-maker" if args.contest_maker else "task-maker"
    if args.shell == "zsh":
        result = zsh_autocomplete(the_parser, command)
    else:
        raise NotImplementedError()
    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
    else:
        print(result)


if __name__ == '__main__':
    main()
