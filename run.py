import os, sys, time, datetime
from optparse import OptionParser
import digitalocean
import digoc_config
import requests

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
opts, args =  parser.parse_args()

print opts
print args

if args or (not opts.image_name) or (not opts.vm_name):
	parser.print_help()
	sys.exit(1)

sshkey_name = "jenkins"

manager = digitalocean.Manager(
			client_id=digoc_config.client_id,
			api_key=digoc_config.api_key)

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

sizes = manager.get_all_sizes()
for size in sizes:
	if (size.name == opts.size):
		break
else:
	raise Exception("Unable to find the %s sshkey", opts.size)

def change_kernel(vm_id):
	print "Boot the 3.11 kernel"
	headers = {'Authorization':'Bearer ' + digoc_config.token}
	headers['content-type'] = 'application/json'
	#  {u'id': 453,
	#   u'name': u'* Fedora 20 x64 vmlinuz-3.11.10-301.fc20.x86_64',
	#   u'version': u'3.11.10-301.fc20.x86_64'},
	req = requests.post("https://api.digitalocean.com/v2/droplets/%s/actions" % vm_id, headers=headers, params={"type" : "change_kernel", "kernel" : 453})
	print req.json()

region = 5
if "linux-next" in opts.image_name:
	region = 3

droplet = digitalocean.Droplet(
			client_id=digoc_config.client_id,
			api_key=digoc_config.api_key,
			name = opts.vm_name,
			size_id=size.id,
			image_id=image.id,
			region_id=region, #ams2
			ssh_key_ids=sshkey.id)
droplet.create()

def wait(droplet):
	events = droplet.get_events()
	event = events[-1]
	while event.percentage != "100":
		time.sleep(1)
		event.load()
		print event.percentage

	droplet.load()

wait(droplet)
if not opts.load_kernel:
	droplet.shutdown()
	wait(droplet)
	change_kernel(droplet.id)
	time.sleep(60) # FIXME
	droplet.power_on()
	wait(droplet)

print droplet.ip_address

ret = 0
for i in xrange(60):
	run_cmd("ip neig flush all");
	if run_cmd("ping -c 1 -W 1 %s" % droplet.ip_address) == 0:
		break;
else:
	ret = 1

fname = "jenkins-%s.tar.gz" % datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
if ret == 0:
	ret = run_cmd("scp -oStrictHostKeyChecking=no -oBatchMode=yes -r jenkins-scripts/ %s:" % droplet.ip_address)

if ret == 0 and opts.load_kernel:
	ret = run_cmd("%s %s bash -x jenkins-scripts/load-kernel.sh /root/linux-next" % (SSH, droplet.ip_address))
	if ret == 0:
		run_cmd("%s %s kexec -e" % (SSH, droplet.ip_address))
	time.sleep(10)
	stime = time.time()
	while time.time() - stime < 60 and ret == 0:
		if run_cmd("%s %s true" % (SSH, droplet.ip_address)) == 0:
			break;
		time.sleep(1)
	else:
		ret = 1

if ret == 0:
	ret = run_cmd("%s %s bash -x jenkins-scripts/jenkins-ct.sh jenkins.sh" % (SSH, droplet.ip_address))
	if ret:
		run_cmd("%s %s tar -czf %s -C criu ." % (SSH, droplet.ip_address, fname))
		run_cmd("scp -oStrictHostKeyChecking=no -oBatchMode=yes %s:%s %s" % (droplet.ip_address, fname, LOGS))
droplet.shutdown()
wait(droplet)
#if ret:
#	droplet.take_snapshot(fname)
#	wait(droplet)
droplet.destroy()
if ret:
	sys.exit(1)
