#!/usr/bin/env bash

cmake -H. -Bbuild -DHUNTER_ENABLED=OFF
cmake --build build
# yee sudo setup.py install!! it's on a container, so... ¯\_(ツ)_/¯
sudo python build/python/setup.py install
( cd build && ctest -VV )
