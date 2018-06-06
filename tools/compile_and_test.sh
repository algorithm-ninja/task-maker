#!/usr/bin/env bash

if [ "$CI" != "true" ]; then
    echo "This script is supposed to run on the CI, it may break your system"
    exit 1
fi

if [ "$TOOLCHAIN" == "archlinux" ]; then
    cmake -H. -Bbuild -DHUNTER_ENABLED=OFF -DTRAVIS=ON
else
    cmake -H. -Bbuild -DHUNTER_ROOT=/hunter-root -DTRAVIS=ON
fi
cmake --build build

# yee sudo setup.py install!! it's on a container, so... ¯\_(ツ)_/¯
sudo python build/python/setup.py install
( cd build && ctest -VV )