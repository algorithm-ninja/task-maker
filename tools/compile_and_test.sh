#!/usr/bin/env bash

set -ex

if [ "$CI" != "true" ]; then
    echo "This script is supposed to run on the CI, it may break your system"
    exit 1
fi

if [ "$TOOLCHAIN" == "archlinux" ]; then
    # the archlinux build user is not root
    python3 -m venv /tmp/venv
    . /tmp/venv/bin/activate
    cmake -H. -Bbuild -DHUNTER_ENABLED=OFF -DTRAVIS=ON
else
    if [ -f /venv/bin/activate ]; then
        . /venv/bin/activate
    fi
    cmake -H. -Bbuild -DHUNTER_ROOT=/hunter-root -DTRAVIS=ON
fi
cmake --build build

# with install the test data is not copied
python build/python/setup.py develop

./build/cpp/task-maker --help || true

( cd build && ctest -VV )
