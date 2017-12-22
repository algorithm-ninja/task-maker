#!/bin/sh
PYTHON_DIR="$(dirname $0)/../../python_repo/python_3_6_files"
export PYTHONNOUSERSITE=true
export PYTHONPATH="$(dirname $0)/.."
LD_LIBRARY_PATH=$PYTHON_DIR/lib exec $PYTHON_DIR/bin/python3 "$@"
