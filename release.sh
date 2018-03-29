#!/bin/bash -e
set -x

cd $(dirname $0)

TEMPDIR=/tmp

bazel build -c opt //python:task_maker
mkdir -p $TEMPDIR/task_maker
cp -r bazel-bin/python/task_maker.runfiles bazel-bin/python/task_maker -L $TEMPDIR/task_maker

pushd $TEMPDIR/task_maker

chmod u+w -R .
for dep in $(cd task_maker.runfiles/; ls -d pypi*)
do
  rm -rf task_maker.runfiles/$dep
  ln -s oii_task_maker/external/$dep task_maker.runfiles
done
find . -type f -name '*.pyc' -delete
rm -rf task_maker.runfiles/oii_task_maker/_solib_k8
find . -type f -name '*.so' | xargs strip -s || true
find . -type f -name 'manager' | xargs strip -s || true
find . -type f -print0 | xargs -0 chmod u-w

popd

mkdir release
zip -r release/task-maker-$CIRCLE_TAG.zip $TEMPDIR/task_maker
