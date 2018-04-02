#!/usr/bin/env python

from collections import deque

BUFFER_SIZE = 1024
FUZZER_LENGTH = 8192
FUZZER_RUNS = 1024
DEFAULT_INT_MAX_LEN = 32
DEFAULT_FLOAT_MAX_LEN = 32
DEFAULT_STRING_MAX_LEN = 4096


class TokenStream:
    def __init__(self, file, strict_spaces=False,
                 int_max_len=DEFAULT_INT_MAX_LEN,
                 float_max_len=DEFAULT_FLOAT_MAX_LEN,
                 str_max_len=DEFAULT_STRING_MAX_LEN, spaces=" \t\n"):
        """
        :param file: file object of the output
        :param strict_spaces: whether to consider spaces as tokens, manual
        skipping of them is required
        :param int_max_len: maximum number of chars for a int
        :param float_max_len: maximum number of chars for a float
        :param str_max_len: maximum number of chars for a str
        :param spaces: list of characters to consider spaces
        """
        self.file = file
        self.strict_spaces = strict_spaces

        if str_max_len < int_max_len:
            raise ValueError("str_max_len lower than int_max_len")
        if str_max_len < float_max_len:
            raise ValueError("str_max_len lower than float_max_len")

        self.int_max_len = int_max_len
        self.float_max_len = float_max_len
        self.str_max_len = str_max_len

        self.spaces = spaces

        self.char_buffer = deque()
        self.current_line_no = 1
        self.eof = False

    # =======================
    #      read a token
    # =======================

    def int(self, validate=lambda x: True):
        """Read an integer"""
        return self._parse_number(self.int_max_len, int, "+-0123456789",
                                  validate, advance_buffer=True)

    def float(self, validate=lambda x: True):
        """Read a float"""
        return self._parse_number(self.float_max_len, float, "+-e0123456789.",
                                  validate, advance_buffer=True)

    def str(self, validate=lambda x: True):
        """Read a string"""
        self._skip_spaces()
        buffer = list()
        # read all chars that are not spaces
        while not self._is_eof() and self._probe_char() not in self.spaces:
            buffer += self._next_char()
            if len(buffer) > self.str_max_len:
                raise ValueError("string too long")
        buffer = "".join(buffer)
        if not validate(buffer):
            raise ValueError("invalid string")
        return buffer

    def char(self, validate=lambda x: True):
        """Read a single char, skipping spaces"""
        self._skip_spaces()
        char = self._next_char()
        if not validate(char):
            raise ValueError("invalid char")
        return char

    def space(self, validate=lambda x: True):
        """Read a single space"""
        if self._is_eof() or self._probe_char() not in self.spaces:
            raise ValueError("expecting a space")
        space = self._next_char()
        if not validate(space):
            raise ValueError("invalid space")
        return space

    def end(self):
        """Check that there are no more tokens before the next testcase
        without consuming anything"""
        # the end of the file is a valid end
        if not self.strict_spaces:
            self._skip_spaces()

        if self._is_eof():
            return
        try:
            # read at least the characters for the prefix and a digit
            while len(self.char_buffer) < len("Case #") + 1:
                self._read_char()
            # check the buffer starts with the prefix
            if self._is_prefix() >= 0:
                raise ValueError("the testcase has not ended")
        # if the EOF is found but not at the beginning there's a problem
        except EOFError:
            raise ValueError("expecting new testcase, not EOF")

    def seek_next_testcase(self):
        """
        skip everything until the next testcase
        @:returns a pair: (testcase number, skipped bytes, line_no)
        @:raises EOFError: when the file ends this error is raised with the
        skipped bytes as args[1]
        """
        old_spaces = self.spaces
        MAX_LEN = 100

        class safe_str:
            def __init__(self):
                self.str = list()
                self.trimmed = False

            def __add__(self, other):
                if len(self.str) > MAX_LEN or self.trimmed:
                    return self
                if len(self.str) + len(other) > MAX_LEN:
                    self.str += list(other[:MAX_LEN - len(self)]) + list("...")
                    self.trimmed = True
                    return self
                self.str += list(other)
                return self

            def __len__(self):
                return len(self.str)

            def __str__(self):
                return "".join(self.str)

        data_read = safe_str()
        skipped_from = self.current_line_no

        while True:
            try:
                skipped = str(data_read)
                skipped_from = self.current_line_no

                # skip all the spaces
                while self._probe_char() in self.spaces:
                    data_read += self._next_char()

                # try to read the "Case"
                case = self.str()
                line = self.current_line_no
                data_read += case
                # if the string is not Case, read also the space and try again
                if case.lower() != "case" and case.lower() != "caso":
                    data_read += self._probe_char()
                    continue

                # skip one space between "Case" and "#"
                data_read += self.space()

                # check if the next char is #
                if self._probe_char() != "#": continue
                # if so read it
                data_read += self.char()

                # to read the testcase number use the ":" as a delimiter,
                # after the int is read revert this change
                self.spaces += ":"
                num = self.int()
                data_read += str(num)
                # revert self.spaces
                self.spaces = old_spaces
                # if the testcase number is not valid
                if num <= 0: continue

                # check if the char after the number is a ":"
                if self._probe_char() != ":": continue
                data_read += self.char()

                return num, line, str(skipped), skipped_from
            except ValueError as ex:
                pass
            except EOFError as ex:
                raise EOFError(ex.args[0], str(data_read), skipped_from)
            finally:
                # if the call to self.int() fails we have to be sure to have
                # reverted self.spaces
                self.spaces = old_spaces

    def has_int(self):
        """check is the next bytes in the buffer are a valid int"""
        if not self.strict_spaces:
            self._skip_spaces()
        try:
            self._parse_number(self.int_max_len, int, "+-0123456789",
                               lambda x: True, advance_buffer=False)
        except:
            return False
        else:
            return True

    def has_float(self):
        """check is the next bytes in the buffer are a valid float"""
        if not self.strict_spaces:
            self._skip_spaces()
        try:
            self._parse_number(self.float_max_len, float, "+-e0123456789.",
                               lambda x: True, advance_buffer=False)
        except:
            return False
        else:
            return True

    def has_space(self, accepted=None):
        """check is the next byte in the buffer is a space (only in
        strict_spaces mode)"""
        if not self.strict_spaces:
            raise RuntimeError(
                "has_space is available only in strict_spaces mode")
        if accepted is None:
            accepted = self.spaces
        return not self._is_eof() and self._probe_char() in accepted

    # ================
    #    utilities
    # ================

    def _skip_spaces(self):
        """Try to skip the spaces, if int strict_spaces mode and there are
        spaces to skip raise an error"""
        if self.strict_spaces and not self._is_eof() and self._probe_char() \
                in self.spaces:
            raise ValueError("expecting something not a space")
        spaces = ""
        while not self._is_eof() and self._probe_char() in self.spaces:
            spaces += self._next_char()
        return spaces

    def _next_char(self):
        """Read and consume a char"""
        if self._probe_char() == "\n":
            self.current_line_no += 1
        return self.char_buffer.popleft()

    def _probe_char(self, index=0):
        """Fetch the next index-th character without consuming it"""
        if len(self.char_buffer) <= index:
            self._read_char()
        return self.char_buffer[index]

    def _read_char(self):
        """Read but not consume a character"""
        char = self.file.read(BUFFER_SIZE)
        if char == "":
            raise EOFError("End of file")
        self.char_buffer.extend(char)
        return char

    def _parse_number(self, max_len, type, allowed_chars, validate,
                      advance_buffer=True):
        """
        Read and parse a number
        :param max_len: maximum number of characters to read
        :param type: int/float
        :param allowed_chars: set of allowed characters in the number
        :param validate: function to call to check if the number is valid
        :param advance_buffer: whether to consume the number
        """
        self._skip_spaces()
        # index in the char_buffer
        index = 0
        buffer = ""
        # continue to read until the end of the file or an invalid char
        while not self._is_eof(index + 1) and self._probe_char(
                index) in allowed_chars:
            buffer += self.char_buffer[index]
            index += 1
            if len(buffer) > max_len:
                raise ValueError("number too long")

        # if the while exited because an invalid char
        if not self._is_eof(index + 1) and self._probe_char(
                index) not in self.spaces:
            raise ValueError(
                "invalid character `%s' in number" % self._probe_char(index))

        # consume the number if requested
        if advance_buffer:
            for _ in range(index):
                self._next_char()

        res = type(buffer)
        if not validate(res):
            raise ValueError("validation failed")
        return res

    def _is_prefix(self):
        """tries to match the "Case #" prefix in the buffer, returns the
        index of mismatch, -1 if match"""
        for i in range(len("Case #")):
            if self.char_buffer[i].lower() != "case #"[i]:
                return i
        return -1

    def _is_eof(self, at_least=1):
        """returns True if there are no more bytes to consume"""
        if len(self.char_buffer) >= at_least:
            return False
        if self.eof:
            return True
        try:
            self._read_char()
        except EOFError:
            self.eof = True
            return True
        else:
            return False


class Parser:
    def __init__(self, parse_testcase, num_inputs, file, **kwargs):
        """
        :param parse_testcase: function to call to parse a testcase, will be
        passed 2 parameters: (testcase number,
        stream). The second parameter is an instance of TokenStream. The
        function may return the score [0,1] or a tuple
        (score, message).
        :param num_inputs: number of testcases
        :param file: file with the output to parse
        :param kwargs: arguments to pass to the TokenStream constructor
        """
        self.stream = TokenStream(file, **kwargs)
        self.parse_testcase = parse_testcase
        self.num_inputs = num_inputs

    def run(self):
        total_score = 0.0
        testcases_seen = set()
        output = {
            "score": 0.0,
            "validation": {
                "cases": [{"status": "missing"} for _ in
                          range(self.num_inputs)],
                "alerts": []
            },
            "feedback": {
                "cases": [{"correct": False} for _ in range(self.num_inputs)],
                "alerts": []
            }
        }

        def add_warning(message):
            output["validation"]["alerts"].append(
                {"severity": "warning", "message": message})

        while True:
            try:
                num, line_no, skipped, skipped_from = \
                    self.stream.seek_next_testcase()
                if len(skipped) > 0:
                    add_warning("Skipped data from line %d: %s" % (
                    skipped_from, skipped))
                if num in testcases_seen:
                    add_warning("Skipped duplicate testcase %d at line %d" % (
                    num, line_no))
                    continue
                if num > self.num_inputs:
                    add_warning("Skipped testcase %d > %d at line %d" % (
                    num, self.num_inputs, line_no))
                    continue
                testcases_seen.add(num)
                output["validation"]["cases"][num - 1]["status"] = "parsed"
                output["validation"]["cases"][num - 1][
                    "message"] = "Found from line %d" % line_no
            except EOFError as ex:
                if len(ex.args) >= 3 and len(ex.args[1]) > 0:
                    add_warning("Skipped data from line %d: %s" % (
                    ex.args[2], ex.args[1]))
                break

            try:
                out = self.parse_testcase(num, self.stream)
            except ValueError as ex:
                output["validation"]["cases"][num - 1]["status"] = "invalid"
                output["validation"]["cases"][num - 1]["message"] = str(ex)
                continue

            if isinstance(out, tuple):
                score, message = out
            else:
                score, message = out, ""

            if len(message) > 0:
                output["feedback"]["cases"][num - 1]["message"] = message
            if score == 1.0:
                output["feedback"]["cases"][num - 1]["correct"] = True
            if score < 0.0 or score > 1.0:
                score = 0.0
                output["feedback"]["cases"][num - 1]["correct"] = False
                output["feedback"]["cases"][num - 1][
                    "message"] = "buggy checker detected!"

            total_score += score

        output["score"] = total_score / self.num_inputs
        return output
