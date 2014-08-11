cd ~/criu &&
git fetch &&
git rebase origin/master &&
git clean -dxf &&
make -j 2 &&
bash -x test/zdtm.sh -C -x '.*\(maps01\|maps04\)' &&
[ "`cat /proc/sys/kernel/tainted`" -eq 0 ] &&
true || { dmesg -k; exit 1}
