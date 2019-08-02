from novaclient import client as nova_client
from novaclient.exceptions import NotFound as NovaNotFound
from cinderclient.exceptions import NotFound as CinderNotFound
from cinderclient import client as cinder_client
from uuid import uuid4
import time

class Driver(object):
    def __init__(self, cloud):
        self._cloud=cloud
        self._credential=cloud.platform_credential
        self._nova_client=nova_client.Client(self._credential['api_version'], username=self._credential['username'], password=self._credential['password'], project_name=self._credential['project_name'], auth_url=self._credential['auth_url'])
        self._cinder_client=cinder_client.Client(self._credential['api_version'],self._credential['username'],self._credential['password'],self._credential['project_name'],auth_url=self._credential['auth_url'])    
        self.instances=InstanceManager(self)
        self.volumes=VolumeManager(self)
        self.images=self._nova_client.glance
        self.flavors=self._nova_client.flavors
        self.keypairs=self._nova_client.keypairs#create, delete

class InstanceManager(object):
    def __init__(self, driver):
        self.driver=driver
        self._manager=driver._nova_client.servers
        self.get=self._manager.get
        self.list=self._manager.list
        self.mountable_status=['ACTIVE','SHUTDOWN']
    def create(self, image_id, template_id, remark='', **kwargs):
        ins=self._manager.create(
            name=remark,
            image=image_id,
            flavor=template_id,
            security_groups=[self.driver._credential['security_group']],
            nics=[{'net-id':self.driver._credential['net-id']}],
            key_name=self.driver._cloud._key_name,
            userdata="#cloud-config\n" \
            "debug: True\n" \
            "ssh_pwauth: True\n" \
            "disable_root: false\n" \
            "runcmd:\n" \
            "- sed -i'.orig' -e's/without-password/yes/' /etc/ssh/sshd_config\n" \
            "- service sshd restart"
        )
        mustend = time.time() + 600
        while time.time() < mustend:
            ins=self.get(ins.id)
            if 'provider' in ins.addresses:
                break
            time.sleep(5)
        return ins
    def delete(self, id):
        try:
            return self._manager.delete(id)
        except NovaNotFound as e:
            print(e)
    def force_delete(self, id):
        return self.delete(id)
    def get_status(self, id):
        ins=self.get(id)
        return ins.status
#TODO ins.stop() return 202
class VolumeManager(object):
    def __init__(self, driver):
        self.driver=driver
        self._manager=driver._cinder_client.volumes
        self.get=self._manager.get
        self.list=self._manager.list
    def create(self, size, remark=''):
        volume=self._manager.create(
            name=remark,
            size=size
        )
        mustend = time.time() + 60
        while time.time() < mustend:
            volume=self.get(volume.id)
            if volume.status == 'available': break
            time.sleep(5)
        return volume
    def delete(self, volume_id):
        mustend = time.time() + 60
        while time.time() < mustend:
            try:
                volume=self._manager.get(volume_id)
            except CinderNotFound as e:
                print(e)
                return
            if volume.status == 'available': break
            time.sleep(5)
        return volume.delete()
    def mount(self, volume_id, instance_id):
        self.driver._nova_client.volumes.create_server_volume(server_id=instance_id, volume_id=volume_id)
        mustend = time.time() + 60
        while time.time() < mustend:
            volume=self.get(volume_id)
            if volume.status == 'in-use': break
            time.sleep(5)
        return volume
    def unmount(self, volume_id, instance_id):
        mustend = time.time() + 60
        while time.time() < mustend:
            ins=self.driver.instances.get(instance_id)
            if ins.status == 'SHUTOFF': break
            time.sleep(5)
        return self.driver._nova_client.volumes.delete_server_volume(server_id=instance_id, volume_id=volume_id)