set -e
home_dir=$(dirname `readlink -f $0`)
kernel_dir=$1
kernel_commit=$2
cd $kernel_dir
git fetch
git fetch --tags
git checkout -f $kernel_commit
git config --global user.email "avagin@openvz.org"
git config --global user.name "Andrew Vagin"
git am $home_dir/fbcon.patch
git describe HEAD
git clean -dxf
cp $home_dir/config .config
make olddefconfig
make -j 2
make modules_install
make install
sync
bash -x $home_dir/reboot.sh `make kernelrelease`
