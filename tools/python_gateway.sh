#!/bin/sh
PYTHON_DIR="$(dirname $0)/../../python_repo/python_3_6_files"
export LD_LIBRARY_PATH="$PYTHON_DIR/lib"
export PYTHONNOUSERSITE=true
export PYTHONHOME="$PYTHON_DIR"
export PYTHONPATH="$(dirname $0)/.."
export PATH="$PYTHON_DIR/bin/:$PATH"
exec $PYTHON_DIR/bin/python3 "$@"
