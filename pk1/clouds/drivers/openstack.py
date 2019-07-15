from novaclient import client as nova_client
from novaclient.exceptions import NotFound as NovaNotFound
from cinderclient.exceptions import NotFound as CinderNotFound
from cinderclient import client as cinder_client
from uuid import uuid4
import time
from ..models import INSTANCE_STATUS

class Driver(object):
    def __init__(self, credential):
        self._credential=credential
        self._nova_client=nova_client.Client(credential['api_version'], username=credential['username'], password=credential['password'], project_name=credential['project_name'], auth_url=credential['auth_url'])
        self._cinder_client=cinder_client.Client(credential['api_version'],credential['username'],credential['password'],credential['project_name'],auth_url=credential['auth_url'])    
        self.instances=InstanceManager(self)
        self.volumes=VolumeManager(self)
        self.images=self._nova_client.glance
        self.flavors=self._nova_client.flavors
        self.keypairs=self._nova_client.keypairs#'create'

class InstanceManager(object):
    def __init__(self, driver):
        self.driver=driver
        self._manager=driver._nova_client.servers
        self.get=self._manager.get
        self.list=self._manager.list
        self.mountable_status=[INSTANCE_STATUS.active.value,INSTANCE_STATUS.shutdown.value]
    def create(self, image_id, template_id, remark='', **kwargs):
        ins=self._manager.create(
            name=remark,
            image=image_id,
            flavor=template_id,
            security_groups=[self.driver._credential['security_group']],
            nics=[{'net-id':self.driver._credential['net-id']}],
            key_name='packone'
        )
        mustend = time.time() + 600
        while time.time() < mustend:
            ins=self.get(ins.id)
            if 'provider' in ins.addresses:
                break
            time.sleep(5)
        return ins
    def delete(self, instance_id):
        try:
            return self._manager.delete(instance_id)
        except NovaNotFound as e:
            print(e)
    def force_delete(self, instance_id):
        return self.delete(instance_id)
    def get_status(self, instance_id):
        ins=self.get(instance_id)
        if ins.status=='ACTIVE':
            return INSTANCE_STATUS.active.value
        elif ins.status=='PAUSED':
            return INSTANCE_STATUS.pause.value
        elif ins.status=='BUILDING':
            return INSTANCE_STATUS.preparing.value
        elif ins.status=='STOPPED':
            return INSTANCE_STATUS.shutdown.value
        elif ins.status=='SHUTOFF':
            return INSTANCE_STATUS.poweroff.value
        elif ins.status=='ERROR':
            return INSTANCE_STATUS.failure.value
        return INSTANCE_STATUS.null.value

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