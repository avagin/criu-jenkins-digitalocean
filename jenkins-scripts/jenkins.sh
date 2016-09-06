#!/bin/bash
set -x
cd ~/criu &&
git remote add avagin https://github.com/avagin/criu.git
git fetch &&
git checkout -f origin/criu-dev &&
git fetch avagin &&
git checkout -f avagin/linux-next &&
git clean -dxf &&
export SKIP_TRAVIS_PREP=1 &&
echo 0 > /sys/fs/cgroup/cpu/tasks &&
./scripts/travis/travis-tests &&
./test/zdtm.py run -T cgroup &&
true || exit 1

#bash -x test/zdtm.sh -C -x '.*\(maps01\|maps04\|tcpbuf\)' &&
[ "`cat /proc/sys/kernel/tainted`" -eq 0 ] &&
( dmesg -k | grep -A 30 ========================= && exit 1 || exit 0 )
exit 0
