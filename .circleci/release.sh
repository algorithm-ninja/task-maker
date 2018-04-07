#!/bin/bash -e
set -x

TEMPDIR=/tmp/task_maker
ROOT=$(echo "$(cd "$(dirname "$0")"; pwd)")/..
CIRCLE_TAG=${CIRCLE_TAG:-unknown}
OUT_FILE=$ROOT/release/task-maker-$CIRCLE_TAG.zip

cd $ROOT

bazel build -c opt //python:task_maker
mkdir -p $TEMPDIR
cp -r bazel-bin/python/task_maker.runfiles bazel-bin/python/task_maker -L $TEMPDIR

pushd $TEMPDIR

chmod u+w -R .
find . -type f -name '*.pyc' -delete
rm -rf task_maker.runfiles/oii_task_maker/_solib_k8
find . -type f -name '*.so' | xargs strip -s || true
find . -type f -name 'manager' | xargs strip -s || true
find . -type f -print0 | xargs -0 chmod u-w

(cd .. && zip -r $OUT_FILE task_maker)

popd