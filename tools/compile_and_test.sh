#!/usr/bin/env bash

cmake -H. -Bbuild -DHUNTER_ENABLED=OFF
cmake --build build
# yee sudo setup.py install!! it's on a container, so... ¯\_(ツ)_/¯
sudo python build/python/setup.py install
#( cd build && ctest -VV )
GLOG_logtostderr=1 GLOG_v=2 ./build/cpp/task-maker -mode manager -port 7071 &
env PYTHONPATH=./build/python python3 ./build/python/task_maker/tests/with_st.py

for f in $(find /tmp -name "task-maker.*"); do
    echo "-------------- $f ------------------"
    cat $f
done