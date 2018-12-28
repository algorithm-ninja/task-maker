#!/usr/bin/env bash

set -xe

HERE="$( cd "$(dirname "$0")" ; pwd -P )"
cd $HERE

names=$(find -name Dockerfile | cut -d"/" -f 2)

for name in $names; do
    HASH=$(git log --pretty=format:"%h" "$HERE/$name/Dockerfile" "$HERE/../CMakeLists.txt" | head -n1)
    DOCKER_CONTAINER_NAME="edomora97/task-maker-builder-$name"
    DOCKER_CONTAINER_ID="$DOCKER_CONTAINER_NAME:$HASH"
    (
        cd "$HERE/$name" &&
        docker build . -t $DOCKER_CONTAINER_ID &&
        docker tag $DOCKER_CONTAINER_ID $DOCKER_CONTAINER_NAME:latest &&
        docker push $DOCKER_CONTAINER_ID &&
        docker push $DOCKER_CONTAINER_NAME:latest
    )
done
