#!/usr/bin/env python

import os.path
from typing import Optional


def detect_format():
    # type: () -> Optional[str]
    ioi = is_ioi_format()
    terry = is_terry_format()
    if ioi and not terry:
        return "ioi"
    elif terry and not ioi:
        return "terry"
    return None


def is_ioi_format():
    # type: () -> bool
    if os.path.isdir("gen") or os.path.isdir("input"):
        return True
    return False


def is_terry_format():
    # type: () -> bool
    if os.path.isdir("managers"):
        return True
    return False
