set -e
cd `dirname $0`
uname -a
unshare -mp -- bash -c "( mount --make-rprivate / && umount -l  /proc && mount -t proc proc /proc/ && bash -x $1)"
