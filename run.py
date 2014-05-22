import digitalocean
import datetime
import time
import os
import sys
import digoc_config

SSH = "ssh -oStrictHostKeyChecking=no -oBatchMode=yes -oServerAliveInterval=15 -oServerAliveCountMax=60 -oPreferredAuthentications=publickey"
LOGS="/home/"
#image_name = "jenkins-3.11-template"
image_name = sys.argv[1]
sshkey_name = "jenkins"
vm_name = "jenkins-test"
load_kernel = sys.argv[2] == "yes"

manager = digitalocean.Manager(
			client_id=digoc_config.client_id,
			api_key=digoc_config.api_key)

images = manager.get_all_images()
image = None
for image in images:
	if (image.name == image_name):
		break
else:
	raise Exception("Unable to find the %s image", image_name)

keys = manager.get_all_sshkeys()
sshkey = None
for sshkey in keys:
	if (sshkey.name == sshkey_name):
		break
else:
	raise Exception("Unable to find the %s sshkey", sshkey_name)

droplet = digitalocean.Droplet(
			client_id=digoc_config.client_id,
			api_key=digoc_config.api_key,
			name = vm_name,
			size_id=66, #512Mb
			image_id=image.id,
			region_id=5, #ams2
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

print droplet.ip_address

ret = 0
for i in xrange(60):
	os.system("ip neig flush all");
	if os.system("ping -c 1 -W 1 %s" % droplet.ip_address) == 0:
		break;
else:
	ret = 1

fname = "jenkins-%s.tar.gz" % datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
if ret == 0:
	ret = os.system("scp -oStrictHostKeyChecking=no -oBatchMode=yes -r jenkins-scripts/ %s:" % droplet.ip_address)

if ret == 0 and load_kernel:
	ret = os.system("%s %s bash -x jenkins-scripts/load-kernel.sh /root/linux-next" % (SSH, droplet.ip_address))
	stime = time.time()
	while time.time() - stime < 60 and ret == 0:
		if os.system("%s %s true" % (SSH, droplet.ip_address)):
			break;
		time.sleep(1)

if ret == 0:
	ret = os.system("%s %s bash -x jenkins-scripts/jenkins-ct.sh jenkins.sh" % (SSH, droplet.ip_address))
	if ret:
		os.system("%s %s tar -czf %s -C criu ." % (SSH, droplet.ip_address, fname))
		os.system("scp -oStrictHostKeyChecking=no -oBatchMode=yes %s:%s %s" % (droplet.ip_address, fname, LOGS))
droplet.shutdown()
wait(droplet)
#if ret:
#	droplet.take_snapshot(fname)
#	wait(droplet)
droplet.destroy()
sys.exit(ret)
