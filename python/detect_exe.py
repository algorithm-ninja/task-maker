#!/usr/bin/env python

# Inspired by
# http://lallouslab.net/2017/07/03/detect-executable-format-using-python/

EXEFLAG_NONE = 0x0000
EXEFLAG_LINUX = 0x0001
EXEFLAG_WINDOWS = 0x0002
EXEFLAG_MACOS = 0x0004
EXEFLAG_MACOS_FAT = 0x0008
EXEFLAG_32BITS = 0x0010
EXEFLAG_64BITS = 0x0020

# Keep signatures sorted by size
_EXE_SIGNATURES = (
    (b"\x4D\x5A", EXEFLAG_WINDOWS),
    (b"\xCE\xFA\xED\xFE", EXEFLAG_MACOS | EXEFLAG_32BITS),
    (b"\xCF\xFA\xED\xFE", EXEFLAG_MACOS | EXEFLAG_64BITS),
    (b"\xBE\xBA\xFE\xCA", EXEFLAG_MACOS | EXEFLAG_32BITS | EXEFLAG_MACOS_FAT),
    (b"\xBF\xBA\xFE\xCA", EXEFLAG_MACOS | EXEFLAG_64BITS | EXEFLAG_MACOS_FAT),
    (b"\x7F\x45\x4C\x46\x01", EXEFLAG_LINUX | EXEFLAG_32BITS),
    (b"\x7F\x45\x4C\x46\x02", EXEFLAG_LINUX | EXEFLAG_64BITS)
)


def get_exeflags(filepath):
    # type: (str) -> int
    with open(filepath, "rb") as file:
        buf = b""
        buf_len = 0
        for sig, flags in _EXE_SIGNATURES:
            sig_len = len(sig)
            if buf_len < sig_len:
                buf += file.read(sig_len - buf_len)
                buf_len = sig_len
            if buf == sig:
                return flags
    return EXEFLAG_NONE
