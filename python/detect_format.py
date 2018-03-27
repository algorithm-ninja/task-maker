#!/usr/bin/env python3

import os.path


def detect_format():
    ioi = is_ioi_format()
    terry = is_terry_format()
    if ioi and not terry:
        return "ioi"
    elif terry and not ioi:
        return "terry"
    return None


def is_ioi_format():
    if os.path.isdir("gen") or os.path.isdir("input"):
        return True
    return False


def is_terry_format():
    if os.path.isdir("managers"):
        return True
    return False