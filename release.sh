#!/bin/bash -e
set -x

DEST=$(pwd)/$1
[ -z "$1" ] && echo "You need to specify an output file!"
[ -z "$1" ] && exit 1

cd $(dirname $0)

TEMPDIR=$(mktemp -d)

cleanup() {
  rm -rf $TEMPDIR
}

trap cleanup EXIT

bazel build -c opt //python:task_maker
mkdir -p $TEMPDIR/task_maker
cp -r bazel-bin/python/task_maker.runfiles bazel-bin/python/task_maker -L $TEMPDIR/task_maker
cd $TEMPDIR/task_maker
chmod u+w -R .
rm task_maker.runfiles/python_repo/ -rf
ln -s oii_task_maker/external/python_repo/ task_maker.runfiles/python_repo
find . -name '*.pyc' -delete
ln -sf libpython3.6m.so.1.0 task_maker.runfiles/oii_task_maker/external/python_repo/python_3_6_files/lib/libpython3.6m.so
rm -rf task_maker.runfiles/oii_task_maker/external/python_repo/python_3_6_files/lib/python3.6/config-3.6m-x86_64-linux-gnu/
rm -rf task_maker.runfiles/oii_task_maker/_solib_k8
find . -name '*.so' | xargs strip -s || true
find . -type f -print0 | xargs -0 chmod u-w

cd ..
tar cv task_maker | xz -9e > $DEST
