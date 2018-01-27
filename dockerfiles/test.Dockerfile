FROM gcc:7.2

RUN echo "deb [arch=amd64] http://storage.googleapis.com/bazel-apt stable jdk1.8" | tee /etc/apt/sources.list.d/bazel.list

RUN curl https://bazel.build/bazel-release.pub.gpg | apt-key add -

RUN apt update && apt upgrade -yy openjdk-8-jdk bazel python3-setuptools python3-wheel python3-virtualenv virtualenv

RUN ln -s /usr/bin/g++-6 /usr/bin/g++ || true
