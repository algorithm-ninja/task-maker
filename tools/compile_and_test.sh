#!/usr/bin/env bash

if [ "$CI" != "true" ]; then
    echo "This script is supposed to run on the CI, it may break your system"
    exit 1
fi

cmake -H. -Bbuild -DHUNTER_ENABLED=OFF -DTRAVIS=ON
cmake --build build
# yee sudo setup.py install!! it's on a container, so... ¯\_(ツ)_/¯
sudo python build/python/setup.py install
( cd build && ctest -VV )

for f in $(find /tmp -name "task-maker.*"); do
    echo "-------------- $f ------------------"
    cat $f
done