#!/usr/bin/env bash

set -ex

python3 -m venv /tmp/venv --system-site-packages
. /tmp/venv/bin/activate
cmake -H. -Bbuild -DHUNTER_ENABLED=OFF -DTRAVIS=ON
cmake --build build
./hooks/lint-all
