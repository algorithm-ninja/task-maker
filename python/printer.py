#!/usr/bin/env python3
import curses


class Printer:
    def text(self, what: str) -> None:
        pass

    def red(self, what: str, bold: bool = True) -> None:
        pass

    def green(self, what: str, bold: bool = True) -> None:
        pass

    def blue(self, what: str, bold: bool = True) -> None:
        pass

    def yellow(self, what: str, bold: bool = True) -> None:
        pass

    def bold(self, what: str, bold: bool = True) -> None:
        pass


class StdoutPrinter(Printer):
    def __init__(self) -> None:
        self.bold_fmt = "\033[1m"
        self.green_fmt = "\033[32m"
        self.red_fmt = "\033[31m"
        self.blue_fmt = "\033[34m"
        self.yellow_fmt = "\033[33m"
        self.reset_fmt = "\033[0m"
        self.right_fmt = "\033[1000C"

    # pylint: disable=no-self-use
    def left_fmt(self, amount: int) -> str:
        return "\033[%dD" % amount

    # pylint: enable=no-self-use

    def text(self, what: str) -> None:
        print(what, end="")

    def red(self, what: str, bold: bool = True) -> None:
        print(
            self.red_fmt + (self.bold_fmt
                            if bold else "") + what + self.reset_fmt,
            end="")

    def green(self, what: str, bold: bool = True) -> None:
        print(
            self.green_fmt + (self.bold_fmt
                              if bold else "") + what + self.reset_fmt,
            end="")

    def blue(self, what: str, bold: bool = True) -> None:
        print(
            self.blue_fmt + (self.bold_fmt
                             if bold else "") + what + self.reset_fmt,
            end="")

    def yellow(self, what: str, bold: bool = True) -> None:
        print(
            self.yellow_fmt + (self.bold_fmt
                               if bold else "") + what + self.reset_fmt,
            end="")

    def bold(self, what: str, bold: bool = True) -> None:
        print(self.bold_fmt + what + self.reset_fmt, end="")

    def right(self, what: str) -> None:
        print(self.right_fmt + self.left_fmt(len(what) - 1) + what)


class CursesPrinter(Printer):
    def __init__(self, stdscr: 'curses._CursesWindow') -> None:
        self.stdscr = stdscr
        self.bold_fmt = curses.A_BOLD
        if curses.COLORS >= 256:
            self.green_fmt = curses.color_pair(82)
        else:
            self.green_fmt = curses.color_pair(curses.COLOR_GREEN)
        self.red_fmt = curses.color_pair(curses.COLOR_RED)
        self.blue_fmt = curses.color_pair(curses.COLOR_BLUE)
        self.yellow_fmt = curses.color_pair(curses.COLOR_YELLOW)

    def text(self, what: str) -> None:
        self.stdscr.addstr(what)

    def red(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.red_fmt | (self.bold_fmt if bold else 0))

    def green(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.green_fmt | (self.bold_fmt
                                                   if bold else 0))

    def blue(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.blue_fmt | (self.bold_fmt
                                                  if bold else 0))

    def yellow(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.yellow_fmt | (self.bold_fmt
                                                    if bold else 0))

    def bold(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.bold_fmt)
