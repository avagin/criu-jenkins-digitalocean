import os, sys, time, datetime
from optparse import OptionParser
import digitalocean
import requests
import imp

def run_cmd(cmd):
	print "Run - ", cmd
	ret = os.system(cmd)
	print "- exits with %d" % ret
	return ret

SSH = "ssh -oStrictHostKeyChecking=no -oBatchMode=yes -oServerAliveInterval=15 -oServerAliveCountMax=60 -oPreferredAuthentications=publickey"
LOGS="/home/"
#opts.image_name = "jenkins-3.11-template"

from optparse import OptionParser
parser = OptionParser()
parser.add_option("--image-name")
parser.add_option("--vm-name")
parser.add_option("--load-kernel", action="store_true", default=False)
parser.add_option("--size", default="512MB")
parser.add_option("--commit", default="origin/master")
parser.add_option("--preserve-vm", action="store_true", default=False)
parser.add_option("--config")
opts, args =  parser.parse_args()

print opts
print args

digoc_config = imp.load_source("digoc_config", opts.config)

if args or (not opts.image_name) or (not opts.vm_name):
	parser.print_help()
	sys.exit(1)

sshkey_name = "jenkins"

manager = digitalocean.Manager()
manager.token = digoc_config.token

images = manager.get_all_images()
for image in images:
	if (image.name == opts.image_name):
		break
else:
	raise Exception("Unable to find the %s image", opts.image_name)

keys = manager.get_all_sshkeys()
for sshkey in keys:
	if (sshkey.name == sshkey_name):
		break
else:
	raise Exception("Unable to find the %s sshkey", sshkey_name)

def change_kernel(vm_id):
	print "Boot the 3.11 kernel"
	headers = {'Authorization':'Bearer ' + digoc_config.token}
	headers['content-type'] = 'application/json'
	#  {u'id': 453,
	#   u'name': u'* Fedora 20 x64 vmlinuz-3.11.10-301.fc20.x86_64',
	#   u'version': u'3.11.10-301.fc20.x86_64'},
	req = requests.post("https://api.digitalocean.com/v2/droplets/%s/actions" % vm_id, headers=headers, params={"type" : "change_kernel", "kernel" : 453})
	print req.json()

region = "ams2"
if "linux-next" in opts.image_name:
	region = "sfo1"

droplet = digitalocean.Droplet(
			token = digoc_config.token,
			name = opts.vm_name,
			size = opts.size,
			image = image.id,
			region = region, #ams2
			ssh_keys=[ sshkey ])
droplet.create()

def wait(droplet):
	events = droplet.get_events()
	for event in events:
		while event.status == u'in-progress':
			time.sleep(1)
			event.load()
			print getattr(event, "percentage", ".")

	droplet.load()

def wait_ssh(ipaddr):
	global SSH
	ret = 0
	for i in xrange(60):
		run_cmd("ip neig flush all");
		if run_cmd("ping -c 1 -W 1 %s" % ipaddr) != 0:
			continue;
		if run_cmd("%s %s true" % (SSH, ipaddr)) == 0:
			break;
	else:
		ret = 1
	return ret


wait(droplet)

print droplet.ip_address
ret = wait_ssh(droplet.ip_address)

if not opts.load_kernel:
	print "Stop VM"
	run_cmd("%s %s halt -p" % (SSH, droplet.ip_address))
	droplet.shutdown()
	wait(droplet)
	time.sleep(30)
	print "Switch kernel"
	for k in droplet.get_kernel_available():
		if k.id == 453:
			print k.name
			break
	droplet.change_kernel(k)
	wait(droplet)
	time.sleep(30)
	print "Start VM"
	droplet.power_on()
	wait(droplet)

print droplet.ip_address
ret = wait_ssh(droplet.ip_address)

fname = "jenkins-%s.tar.gz" % datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
if ret == 0:
	ret = run_cmd("scp -oStrictHostKeyChecking=no -oBatchMode=yes -r jenkins-scripts/ %s:" % droplet.ip_address)

if ret == 0 and opts.load_kernel:
	run_cmd("%s %s yum install -y openssl-devel" % (SSH, droplet.ip_address))
	ret = run_cmd("%s %s bash -x jenkins-scripts/load-kernel.sh /root/linux-next %s" % (SSH, droplet.ip_address, opts.commit))
	if ret == 0:
		run_cmd("%s %s kexec -e" % (SSH, droplet.ip_address))
	time.sleep(10)
	stime = time.time()
	for i in xrange(10):
		if ret != 0:
			break
		if run_cmd("%s %s true" % (SSH, droplet.ip_address)) == 0:
			break;
		time.sleep(30)
	else:
		ret = 1

if ret == 0:
	run_cmd("%s %s  modprobe ip6table_filter" % (SSH, droplet.ip_address))
	run_cmd("%s %s yum update -y" % (SSH, droplet.ip_address));
	run_cmd("%s %s yum install -y libcap-devel libaio-devel.x86_64 protobuf-devel.x86_64 libnl3-devel PyYAML glibc-devel.i686 protobuf-python.x86_64" % (SSH, droplet.ip_address))
	ret = run_cmd("%s %s bash -x jenkins-scripts/jenkins-ct.sh jenkins.sh" % (SSH, droplet.ip_address))
	if ret:
		run_cmd("%s %s dmesg > dmesg.log" % (SSH, droplet.ip_address))
		run_cmd("%s %s tar -cz -C criu . > log.tar.gz" % (SSH, droplet.ip_address))
#		run_cmd("%s %s tar -czf %s -C criu ." % (SSH, droplet.ip_address, fname))
#		run_cmd("scp -oStrictHostKeyChecking=no -oBatchMode=yes %s:%s %s" % (droplet.ip_address, fname, LOGS))
if not opts.preserve_vm:
	droplet.shutdown()
	wait(droplet)
	#if ret:
	#	droplet.take_snapshot(fname)
	#	wait(droplet)droplet.destroy()
	droplet.destroy()
if ret:
	sys.exit(1)
