FROM ubuntu:16.04
MAINTAINER Edoardo Morassutto <edoardo.morassutto@gmail.com>

ENV CC=gcc CXX=g++

RUN mkdir -p /build

WORKDIR /build

# setup the system
# yes, i feel guilty for "pip install", but it's only for the tests
RUN apt update -y && \
    apt install -y g++ gcc git make libdw-dev wget \
                   python3 python3-setuptools python3-pip \
                   python3-traits python3-ruamel.yaml python3-pytoml \
                   fpc rustc zip && \
    apt-get clean && \
    ln -sf $(which $CC) /usr/bin/cc && \
    ln -sf $(which $CXX) /usr/bin/c++ && \
    pip3 install pytest

RUN wget -O installer.sh https://github.com/Kitware/CMake/releases/download/v3.13.0/cmake-3.13.0-Linux-x86_64.sh && \
    sh installer.sh --skip-license --prefix=/usr && \
    rm installer.sh

RUN mkdir /hunter-root

# prebuild the hunter packages
RUN git clone https://github.com/algorithm-ninja/task-maker /tmp/task-maker && \
    cd /tmp/task-maker && \
    cmake -H. -Bbuild -DHUNTER_ROOT=/hunter-root && \
    cd / && \
    rm -rf /tmp/task-maker
