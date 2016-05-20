cd ~/criu &&
git fetch &&
git checkout -f origin/criu-dev &&
git clean -dxf &&
make -j 2 &&
make -j 2 -C test/zdtm &&
echo 0 > /sys/fs/cgroup/cpu/tasks &&
./test/zdtm.py run --all --report report --parallel 2 -x 'maps04' -x 'maps01' &&
true || exit 1

#bash -x test/zdtm.sh -C -x '.*\(maps01\|maps04\|tcpbuf\)' &&
[ "`cat /proc/sys/kernel/tainted`" -eq 0 ] &&
( dmesg -k | grep -A 30 ========================= && exit 1 || exit 0 )
exit 0
