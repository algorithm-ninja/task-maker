FROM ubuntu:14.04
MAINTAINER Edoardo Morassutto <edoardo.morassutto@gmail.com>

ENV UGID='2000' UGNAME='travis'
ENV CC=gcc-7 CXX=g++-7 PATH=/cmake/cmake-3.11.1-Linux-x86_64/bin:$PATH

# setup the system
RUN groupadd --gid "$UGID" "$UGNAME" && \
    useradd --create-home --uid "$UGID" --gid "$UGID" "${UGNAME}" && \
    apt update -y && \
    apt install -y software-properties-common && \
    apt-add-repository -y ppa:ubuntu-toolchain-r/test && \
    apt-add-repository -y ppa:jonathonf/python-3.6 && \
    apt update -y && \
    apt install -y g++-7 git make python3.6 python3.6-dev wget rustc zip sudo && \
    apt-get clean && \
    echo "travis ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$UGNAME && \
    ln -sf $(which $CC) /usr/bin/cc && \
    ln -sf $(which $CXX) /usr/bin/c++ && \
    wget -O /tmp/cmake.tar.gz "https://cmake.org/files/v3.11/cmake-3.11.1-Linux-x86_64.tar.gz" && \
    mkdir /cmake && tar xf /tmp/cmake.tar.gz -C /cmake && \
    python3.6 -m venv /venv --without-pip && \
    . /venv/bin/activate && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py && \
    mkdir /hunter-root && chown -R $UGID:$UGID /hunter-root /venv

USER $UGNAME

RUN . /venv/bin/activate && \
    git clone https://github.com/algorithm-ninja/task-maker /tmp/task-maker && \
    cd /tmp/task-maker && \
    cmake -H. -Bbuild -DHUNTER_ROOT=/hunter-root && \
    cd / && \
    rm -rf /tmp/task-maker

RUN sudo mkdir -p /build

WORKDIR /build