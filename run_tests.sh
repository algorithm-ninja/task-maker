#/bin/bash

echo -n "Building..."

( mkdir -p build &&  cd build && cmake .. && make -j8 ) &> /dev/null

if [ $? -ne 0 ]
then
  echo " failure"
  exit 1
fi


echo " done"

export TEST_TMPDIR=/tmp/task_maker_testdir
mkdir -p ${TEST_TMPDIR}

cleanup() {
  rm -rf ${TEST_TMPDIR}
}

trap cleanup EXIT

( cd build/cpp && ./sandbox_unix_test )
