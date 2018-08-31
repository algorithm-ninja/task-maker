#!/usr/bin/env python3

import os
import sys


def patch_sys_path():
    sys.path.append(os.path.join(os.path.dirname(__file__), 'venv'))
