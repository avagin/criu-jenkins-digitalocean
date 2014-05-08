unshare -mp -- bash -c "( mount --make-rprivate / && umount -l  /proc && mount -t proc proc /proc/ && bash -x jenkins.sh)"
