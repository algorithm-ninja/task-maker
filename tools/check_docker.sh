#!/usr/bin/env bash

set -xe

function docker_tag_exists() {
    curl --silent -f -lSL https://index.docker.io/v1/repositories/$1/tags/$2 > /dev/null
}

HERE="$( cd "$(dirname "$0")" ; pwd -P )"
TOOLCHAIN=${TOOLCHAIN:-}

if [ -z "$TOOLCHAIN" ]; then
    echo "Missing TOOLCHAIN variable"
    exit 1
fi

if [ ! -f "$HERE/$TOOLCHAIN/Dockerfile" ]; then
    echo "Invalid toolchain '$TOOLCHAIN'"
    exit 1
fi

HASH=$(git log --pretty=format:"%h" "$HERE/$TOOLCHAIN/Dockerfile" | head -n1)
DOCKER_CONTAINER_NAME="edomora97/task-maker-builder-$TOOLCHAIN"
DOCKER_CONTAINER_ID="$DOCKER_CONTAINER_NAME:$HASH"

if docker_tag_exists $DOCKER_CONTAINER_NAME $HASH; then
    echo "The docker image is up to date"
else
    (
        cd "$HERE/$TOOLCHAIN" &&
        docker build . -t $DOCKER_CONTAINER_ID &&
        docker tag $DOCKER_CONTAINER_ID $DOCKER_CONTAINER_NAME:latest &&
        docker push $DOCKER_CONTAINER_ID &&
        docker push $DOCKER_CONTAINER_NAME:latest
    )
fi

docker pull $DOCKER_CONTAINER_NAME:latest
