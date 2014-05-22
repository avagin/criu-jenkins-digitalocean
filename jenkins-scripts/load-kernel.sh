set -e
home_dir=$(dirname `readlink -f $0`)
kernel_dir=$1
cd $kernel_dir
git fetch
git checkout -f origin/master
git describe HEAD
git clean -dxf
cp $home_dir/config .config
make olddefconfig
make -j 2
make modules_install
make install
sync
bash -x $home_dir/reboot.sh `make kernelrelease`
