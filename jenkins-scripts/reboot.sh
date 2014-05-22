set -e
kernel_release=$1
kexec -l /boot/vmlinuz-$kernel_release --initrd=/boot/initramfs-$kernel_release.img --command-line="`cat /proc/cmdline`"
#kexec -e
