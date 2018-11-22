FROM base/archlinux
MAINTAINER Edoardo Morassutto <edoardo.morassutto@gmail.com>

RUN mkdir -p /build

WORKDIR /build

ENV UGID='2000' UGNAME='travis'

# setup the system
RUN groupadd --gid "$UGID" "$UGNAME" && \
    useradd --create-home --uid "$UGID" --gid "$UGID" "${UGNAME}" && \
    echo 'Server = http://mirrors.evowise.com/archlinux/$repo/os/$arch' > /etc/pacman.d/mirrorlist && \
    echo 'Server = http://mirror.rackspace.com/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist && \
    echo 'Server = https://mirrors.kernel.org/archlinux/$repo/os/$arch' >> /etc/pacman.d/mirrorlist && \
    pacman -Syu --needed --noconfirm base-devel git sudo yajl && \
    pacman -Scc --noconfirm && \
    echo "travis ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$UGNAME

USER $UGNAME

# install yay
RUN cd /tmp && \
    git clone https://aur.archlinux.org/yay-bin.git && \
    cd yay-bin && \
    makepkg -s && \
    find -name "*pkg.tar.xz" | xargs sudo pacman --noconfirm -U


# install dependencies
RUN yay -Syu --needed --noconfirm --mflags --nocheck \
        python cmake gmock gtest capnproto pybind11 \
        python-pytest python-ruamel-yaml python-traits python-pytoml \
        fpc rust erlang && \
    sudo pacman -Scc --noconfirm
