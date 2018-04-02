#!/usr/bin/env python

from __future__ import print_function

import curses


class Printer:
    def text(self, what):
        # type: (str) -> None
        pass

    def red(self, what, bold=True):
        # type: (str, bool) -> None
        pass

    def green(self, what, bold=True):
        # type: (str, bool) -> None
        pass

    def blue(self, what, bold=True):
        # type: (str, bool) -> None
        pass

    def bold(self, what, bold=True):
        # type: (str, bool) -> None
        pass


class StdoutPrinter(Printer):
    def __init__(self):
        # type: () -> None
        def _get_color(color):
            # type: (int) -> str
            return curses.tparm(curses.tigetstr("setaf"), color).decode("utf8")

        self.bold_fmt = curses.tparm(curses.tigetstr("bold")).decode()
        if curses.COLORS >= 256:
            self.green_fmt = _get_color(82)
        else:
            self.green_fmt = _get_color(curses.COLOR_GREEN)
        self.red_fmt = _get_color(curses.COLOR_RED)
        self.blue_fmt = _get_color(curses.COLOR_BLUE)
        self.reset_fmt = curses.tparm(curses.tigetstr("sgr0")).decode()
        self.right_fmt = curses.tparm(curses.tigetstr("cuf"), 1000).decode()

    # pylint: disable=no-self-use
    def left_fmt(self, amount):
        # type: (int) -> str
        return curses.tparm(curses.tigetstr("cub"), amount).decode()

    # pylint: enable=no-self-use

    def text(self, what):
        # type: (str) -> None
        print(what, end="")

    def red(self, what, bold=True):
        # type: (str, bool) -> None
        print(
            self.red_fmt + (self.bold_fmt
                            if bold else "") + what + self.reset_fmt,
            end="")

    def green(self, what, bold=True):
        # type: (str, bool) -> None
        print(
            self.green_fmt + (self.bold_fmt
                              if bold else "") + what + self.reset_fmt,
            end="")

    def blue(self, what, bold=True):
        # type: (str, bool) -> None
        print(
            self.blue_fmt + (self.bold_fmt
                             if bold else "") + what + self.reset_fmt,
            end="")

    def bold(self, what, bold=True):
        # type: (str, bool) -> None
        print(self.bold_fmt + what + self.reset_fmt, end="")

    def right(self, what):
        # type: (str) -> None
        print(self.right_fmt + self.left_fmt(len(what) - 1) + what)


class CursesPrinter(Printer):
    def __init__(self, stdscr):
        # type: (curses._CursesWindow) -> None
        self.stdscr = stdscr
        self.bold_fmt = curses.A_BOLD
        if curses.COLORS >= 256:
            self.green_fmt = curses.color_pair(82)
        else:
            self.green_fmt = curses.color_pair(curses.COLOR_GREEN)
        self.red_fmt = curses.color_pair(curses.COLOR_RED)
        self.blue_fmt = curses.color_pair(curses.COLOR_BLUE)

    def text(self, what):
        # type: (str) -> None
        self.stdscr.addstr(what)

    def red(self, what, bold=True):
        # type: (str, bool) -> None
        self.stdscr.addstr(what, self.red_fmt | (self.bold_fmt if bold else 0))

    def green(self, what, bold=True):
        # type: (str, bool) -> None
        self.stdscr.addstr(what, self.green_fmt | (self.bold_fmt
                                                   if bold else 0))

    def blue(self, what, bold=True):
        # type: (str, bool) -> None
        self.stdscr.addstr(what, self.blue_fmt | (self.bold_fmt
                                                  if bold else 0))

    def bold(self, what, bold=True):
        # type: (str, bool) -> None
        self.stdscr.addstr(what, self.bold_fmt)
