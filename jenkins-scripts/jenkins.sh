cd ~/criu &&
git fetch &&
git rebase origin/master &&
git clean -dxf &&
make -j 2 &&
bash -x test/zdtm.sh -C -x '.*\(maps01\|maps04\|tcpbuf\)' &&
[ "`cat /proc/sys/kernel/tainted`" -eq 0 ] &&
( dmesg -k | grep -A 30 ========================= && exit 1 || exit 0 ) &&
true || exit 1
