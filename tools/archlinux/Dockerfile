FROM base/archlinux
MAINTAINER Edoardo Morassutto <edoardo.morassutto@gmail.com>

ENV UGID='2000' UGNAME='travis'

# setup the system
RUN groupadd --gid "$UGID" "$UGNAME" && \
    useradd --create-home --uid "$UGID" --gid "$UGID" "${UGNAME}" && \
    pacman -Syu --needed --noconfirm base-devel git sudo yajl && \
    pacman -Scc --noconfirm && \
    echo "travis ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$UGNAME

USER $UGNAME

# install yaourt
RUN cd /tmp && \
    git clone https://aur.archlinux.org/package-query.git && \
    cd package-query && \
    makepkg -s && \
    find -name "*pkg.tar.xz" | xargs sudo pacman --noconfirm -U && \
    cd /tmp && \
    git clone https://aur.archlinux.org/yaourt.git && \
    cd yaourt && \
    makepkg -s && \
    find -name "*pkg.tar.xz" | xargs sudo pacman --noconfirm -U


# install dependencies
RUN yaourt -Syua --needed --noconfirm \
        python python-pip cmake rust gflags gmock google-glog gtest protobuf \
        fpc erlang \
        grpc nlohmann-json-bin && \
    sudo pacman -Scc --noconfirm

RUN sudo mkdir -p /build

WORKDIR /build