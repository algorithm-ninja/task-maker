#!/usr/bin/env bash

set -ex

if [ "$CI" != "true" ]; then
    echo "This script is supposed to run on the CI, it may break your system"
    exit 1
fi

if [ "$TOOLCHAIN" == "archlinux" ]; then
    python3 -m venv /tmp/venv
    . /tmp/venv/bin/activate
    cmake -H. -Bbuild -DHUNTER_ENABLED=OFF -DTRAVIS=ON
else
    . /venv/bin/activate
    cmake -H. -Bbuild -DHUNTER_ROOT=/hunter-root -DTRAVIS=ON
fi
cmake --build build

python build/python/setup.py install

./build/cpp/task-maker -help

( cd build && ctest -VV )