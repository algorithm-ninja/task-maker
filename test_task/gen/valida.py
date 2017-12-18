#!/usr/bin/env python3

import sys
from limiti import *

assert len(sys.argv) == 3
infile = open(sys.argv[1]).read().splitlines()
assert 0 <= int(infile[0]) <= MAX_N
assert 1 <= int(sys.argv[2]) <= 3
