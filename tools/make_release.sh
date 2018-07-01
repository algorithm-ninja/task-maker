#!/usr/bin/env bash

if [ "$TRAVIS_OS_NAME" == "linux" ]; then
    source /venv/bin/activate
else
    source /tmp/venv/bin/activate
fi

cmake -H. -Bbuild_rel -DHUNTER_ROOT=hunter-root -DCMAKE_BUILD_TYPE=Release

cmake --build build_rel

if [ "$TRAVIS_OS_NAME" == "linux" ]; then
    strip -s build_rel/python/task_maker/bin/task-maker
else
    strip build_rel/python/task_maker/bin/task-maker
fi

chmod +x build_rel/python/setup.py

( cd build_rel/python && zip -r task-maker-$TRAVIS_TAG-$TRAVIS_OS_NAME.zip requirements.txt setup.py task_maker )