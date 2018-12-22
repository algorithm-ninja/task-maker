#!/usr/bin/env python3
import curses


class Printer:
    """
    Utility class to print to various types of terminals. This class won't
    print anything, to print use one of the subclasses.
    """

    def text(self, what: str) -> None:
        """
        Normal, unformatted string, the newline won't be added automatically
        """
        pass

    def red(self, what: str, bold: bool = True) -> None:
        """
        Print some text in red, optionally also in bold, the newline won't be
        added automatically.
        """
        pass

    def green(self, what: str, bold: bool = True) -> None:
        """
        Print some text in green, optionally also in bold, the newline won't be
        added automatically.
        """
        pass

    def blue(self, what: str, bold: bool = True) -> None:
        """
        Print some text in blue, optionally also in bold, the newline won't be
        added automatically.
        """
        pass

    def yellow(self, what: str, bold: bool = True) -> None:
        """
        Print some text in yellow, optionally also in bold, the newline won't be
        added automatically.
        """
        pass

    def bold(self, what: str, bold: bool = True) -> None:
        """
        Print some text in bold, the newline won't be added automatically.
        """
        pass


class StdoutPrinter(Printer):
    """
    Printer that will print to stdout using the escape sequences to make the
    colors and so on.
    """

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
            self.red_fmt + (self.bold_fmt if bold else "") + what +
            self.reset_fmt,
            end="")

    def green(self, what: str, bold: bool = True) -> None:
        print(
            self.green_fmt + (self.bold_fmt if bold else "") + what +
            self.reset_fmt,
            end="")

    def blue(self, what: str, bold: bool = True) -> None:
        print(
            self.blue_fmt + (self.bold_fmt if bold else "") + what +
            self.reset_fmt,
            end="")

    def yellow(self, what: str, bold: bool = True) -> None:
        print(
            self.yellow_fmt + (self.bold_fmt if bold else "") + what +
            self.reset_fmt,
            end="")

    def bold(self, what: str, bold: bool = True) -> None:
        print(self.bold_fmt + what + self.reset_fmt, end="")

    def right(self, what: str) -> None:
        """
        Print the text aligned to the right of the screen
        """
        print(self.right_fmt + self.left_fmt(len(what) - 1) + what)


class CursesPrinter(Printer):
    """
    Printer that will use the curses API in a curses Window.
    """

    def __init__(self, stdscr: 'curses._CursesWindow') -> None:
        self.stdscr = stdscr
        self.bold_fmt = curses.A_BOLD
        if hasattr(curses, "COLORS") and curses.COLORS >= 256:
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
        self.stdscr.addstr(what,
                           self.green_fmt | (self.bold_fmt if bold else 0))

    def blue(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what,
                           self.blue_fmt | (self.bold_fmt if bold else 0))

    def yellow(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what,
                           self.yellow_fmt | (self.bold_fmt if bold else 0))

    def bold(self, what: str, bold: bool = True) -> None:
        self.stdscr.addstr(what, self.bold_fmt)
