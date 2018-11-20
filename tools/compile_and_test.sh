#!/usr/bin/env bash

set -ex

if [ "$CI" != "true" ]; then
    echo "This script is supposed to run on the CI, it may break your system"
    exit 1
fi

if [ "$TOOLCHAIN" == "archlinux" ]; then
    # ensure that the system is up-to-date
    yay -Syu --needed --noconfirm --mflags --nocheck
    # the archlinux build user is not root
    python3 -m venv /tmp/venv --system-site-packages
    . /tmp/venv/bin/activate
    cmake -H. -Bbuild -DHUNTER_ENABLED=OFF -DTRAVIS=ON -DADDRESSSANITIZER=$ADDRESSSANITIZER
    cmake --build build
    # with install the test data is not copied
    python3 build/python/setup.py develop
    ( cd build && ctest -VV )
else
    cmake -H. -Bbuild -DHUNTER_ROOT=/hunter-root -DTRAVIS=ON
    cmake --build build
    # with install the test data is not copied
    python3 build/python/setup.py develop
    ( cd build && ctest -VV )
    # for some reason cmake gtest discovery is a bit bugged on ubuntu, manual execution for now
    if [ "$TOOLCHAIN" == "ubuntu16.04" ]; then
        ( cd build/cpp && ./sandbox_unix_test --gtest_list_tests | tail -n +3 | xargs -I{} ./sandbox_unix_test --gtest_filter="UnixTest.{}" )
    fi
fi
