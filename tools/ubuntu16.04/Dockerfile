FROM ubuntu:16.04
MAINTAINER Edoardo Morassutto <edoardo.morassutto@gmail.com>

ENV CC=gcc CXX=g++

RUN mkdir -p /build

WORKDIR /build

# setup the system
RUN apt update -y && \
    apt install -y g++ gcc git cmake make libdw-dev \
                   python3 python3-dev python3-venv \
                   fpc rustc zip && \
    apt-get clean && \
    ln -sf $(which $CC) /usr/bin/cc && \
    ln -sf $(which $CXX) /usr/bin/c++

RUN python3 -m venv /venv && \
    . /venv/bin/activate && \
    mkdir /hunter-root

# prebuild the hunter packages
RUN . /venv/bin/activate && \
    git clone https://github.com/algorithm-ninja/task-maker /tmp/task-maker && \
    cd /tmp/task-maker && \
    cmake -H. -Bbuild -DHUNTER_ROOT=/hunter-root && \
    cd / && \
    rm -rf /tmp/task-maker
