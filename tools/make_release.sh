#!/usr/bin/env bash

set -ex

if [ "$CI" != "true" ]; then
    echo "This script is supposed to run on the CI, it may break your system"
    exit 1
fi

if [ "$TOOLCHAIN" == "archlinux" ]; then
    # ensure that the system is up-to-date
    yay -Syu --needed --noconfirm --mflags --nocheck
    cp -r . /tmp/task-maker
    git clone https://aur.archlinux.org/task-maker-git.git release
    mkdir release/src
    mv /tmp/task-maker release/src/task-maker
    cd release
    sed -i "s/pkgver=.*/pkgver=${TRAVIS_TAG:1}/" PKGBUILD
    source PKGBUILD
    yay --needed --noconfirm --mflags --nocheck -S ${makedepends[*]}
    makepkg -e
    mv $(find -name "*.tar.xz") ../${RELEASE_FILE}
elif [ "$TOOLCHAIN" == "osx" ]; then
    source /tmp/venv/bin/activate
    cmake -H. -Bbuild_rel -DHUNTER_ROOT=hunter-root -DCMAKE_BUILD_TYPE=Release
    cmake --build build_rel
    strip build_rel/python/task_maker/bin/task-maker
    # TODO strip the frontend?
    chmod +x build_rel/python/setup.py
    # TODO build something?
else
    apt install -y lintian
    cmake -H. -Bbuild_rel -DHUNTER_ROOT=hunter-root -DCMAKE_BUILD_TYPE=Release
    cmake --build build_rel
    strip -s build_rel/python/task_maker/bin/task-maker
    strip -s build_rel/python/task_maker/task_maker_frontend.so
    chmod +x build_rel/python/setup.py
    cd build_rel/python
    ./setup.py install --root=root --prefix=/usr --optimize=1
    find root -name __pycache__ -exec rm -rv "{}" +
    find -name site-packages | sed -e "p;s/site/dist/" | xargs -n2 mv
    cp -r ../DEBIAN root
    dpkg-deb --build root ../../${RELEASE_FILE}
    lintian ../../${RELEASE_FILE} -i || true
fi
