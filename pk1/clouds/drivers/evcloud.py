import coreapi
from django.conf import settings
from ..models import INSTANCE_STATUS
#TODO directly use libvirt and ceph

class Driver(object):
    def __init__(self, cloud, credential):
        self._cloud=cloud
        self._credential=credential
        self._client=coreapi.Client(auth=coreapi.auth.BasicAuthentication(credential['user'], credential['passwd']))
        self._schema = self._client.get(credential['api_endpoint'])
        self.instances=InstanceManager(self)
        self.volumes=VolumeManager(self)
        self.images=ImageManager(self)
        self.flavors=FlavorManager()
        self.keypairs=KeyManager()
    def _do_action(self, action, params):
        return self._client.action(self._schema, action, params=params)

class KeyManager(object):
    def create(self, name, public_key):
        return None
    def delete(self, name, public_key):
        return None

class FlavorManager(object):
    def list(self):
        return [
            Flavor({'id': '0', 'name': 'm1.nano', 'ram': 64, 'vcpus': 1}),
            Flavor({'id': '1', 'name': 'm1.tiny', 'ram': 512, 'vcpus': 1}),
            Flavor({'id': '2', 'name': 'm1.small', 'ram': 2048, 'vcpus': 1}),
            Flavor({'id': '3', 'name': 'm1.medium', 'ram': 4096, 'vcpus': 2}),
            Flavor({'id': '4', 'name': 'm1.large', 'ram': 8192, 'vcpus': 2}),
            Flavor({'id': '5', 'name': 'm1.xlarge', 'ram': 16384, 'vcpus': 4}),
            Flavor({'id': '6', 'name': 'm1.xxlarge', 'ram': 32768, 'vcpus': 8}),
            Flavor({'id': '7', 'name': 'm1.xxxlarge', 'ram': 65536, 'vcpus': 16}),
            Flavor({'id': '8', 'name': 'packone.m', 'ram': 8192, 'vcpus': 2}),
            Flavor({'id': '9', 'name': 'packone.m+', 'ram': 1024, 'vcpus': 2}),
            Flavor({'id': '10', 'name': 'packone.l', 'ram': 16384, 'vcpus': 4}),
            Flavor({'id': '11', 'name': 'packone.x', 'ram': 32768, 'vcpus': 8}),
        ]
    def get(self, id):
        for tpl in self.list():
            if tpl.id==id:
                return tpl
        raise Exception('unfounded flavor (id: {})!'.format(id))
 
class Flavor(object):
    def __init__(self, info):
        self.id=info['id']
        self.name=info['name']
        self.ram=info['ram']
        self.vcpus=info['vcpus']

class ImageManager(object):
    def __init__(self, driver):
        self.driver=driver
    def list(self):
        action = ["images","list"]
        params = {
            "pool_id":self.driver._credential['image_poll_id'],
        }
        infos=self.driver._do_action(action,params)
        images=[]
        for info in infos:
            images.append(Image(info))
        return images

class Image(object):
    def __init__(self, info):
        self.id=info['id']
        self.name=info['name']
        if self.name=='centos7': self.name='CentOS-7.5.1804-x86_64-GenericCloud-1809'
        from django.utils.timezone import now
        self.created_at=now()
        if self.name.startswith('0000_packone'):#TODO auto build packone images
            self.name=self.name.replace('0000_','')

class InstanceManager(object):
    def __init__(self, driver):
        self.driver=driver
        self.mountable_status=[INSTANCE_STATUS.shutdown.value, INSTANCE_STATUS.poweroff.value]
    def get(self, instance_id):
        action = ["vms","read"]
        params = {
            "vm_id": instance_id
        }
        info=self.driver._do_action(action, params)
        return Instance(self, info)
    def list(self):
        action = ["vms", "list"]
        params = {
            "group_id":self.driver._credential['group_id'],
        }
        inss=[]
        for item in self.driver._do_action(action, params):
            inss.append(Instance(self, item))
        return inss
    def create(self, image_id, template_id, remark='', **kwargs):
        flavor=self.driver.flavors.get(template_id)
        action = ["vms","create"]
        params = {
            "image_id":int(image_id),
            "vcpu":flavor.vcpus,
            "mem":flavor.ram,
            "group_id":self.driver._credential['group_id'],
            'vlan_id':self.driver._credential['vlan_id'],
            "remarks":remark,
        }
        vm_id=self.driver._do_action(action, params)
        ins=self.get(vm_id)
        ins.start()
        from ..utils import SSH
        ssh=SSH(ins.addresses['provider'][0]['addr'],self.driver._credential['instance_username'],password=self.driver._credential['instance_password'])
        pub=self.driver._cloud._public_key
        ssh.exec_batch('HM=~{}; cd $HM; mkdir -p .ssh; cd .ssh; echo "{}">>authorized_keys; chmod 400 authorized_keys'.format(self.driver._cloud.instance_credential_username, pub))
        ssh.close()
        ins._operate('shutdown') #avoid disk cache lost
        ins.stop()
        return ins
    def create_image(self, image_name):
        raise Exception('create image from instance is unsupported')
    def delete(self, instance_id):
        action = ["vms","delete"]
        params = {
            "vm_id": instance_id,
        }
        try:
            return self.driver._do_action(action, params)
        except coreapi.exceptions.ErrorMessage as e:
            if '\u865a\u62df\u673aUUID\u9519\u8bef' in e.error._data['detail']:
                print('VM UUID Mismatch')
                return True
            else:
                raise e
    def force_delete(self, instance_id):
        try:
            self.get(instance_id).stop()
        except Exception as e:
            print(e)
        return self.delete(instance_id)
    def get_status(self, instance_id):
        action = ["vms","status","list"]
        params = {
            "vm_id":instance_id
        }
        try:
            return int(self.driver._do_action(action,params))
        except coreapi.exceptions.ErrorMessage as e:
            if '\u865a\u62df\u673aUUID\u9519\u8bef' in e.error._data['detail']:
                print('VM UUID Mismatch')
                return 5
            else:
                raise e

class Instance(object):
    def __init__(self, manager, info):
        self.manager=manager
        self.id=info['uuid']
        # self.flavor=self.manager.driver.templates._locate(info['vcpus'], info['mem'])
        self.addresses={}
        if info['ipv4']: self.addresses['provider']=[{'addr': info['ipv4']}]
        self.name=info['remarks']
        self.created=info['create_time']
    def get_console_url(self):
        return {
            'console': {'url': self.manager.driver._do_action(["vms","vnc","create"], {"vm_id":self.id})}
        }
    def _operate(self, op):
        action = ["vms","operations","partial_update"]
        params = {"vm_id":self.id,"op":op}
        try:
            return self.manager.driver._do_action(action, params)
        except coreapi.exceptions.ErrorMessage as e:
            if 'not running' in e.error._data['detail'] or 'already running' in e.error._data['detail']:
                print(e.error._data['detail'])
                return True
            else:
                raise e
    def start(self):
        return self._operate('start')
    def reboot(self):
        return self._operate('reboot')
    def stop(self):
        return self._operate('poweroff')

class VolumeManager(object):
    def __init__(self, driver):
        self.driver=driver
    def _operate_volume(self, volume_id, instance_id, op):
        action = ["volumes","vm","partial_update"]
        params = {
            "volume_id":volume_id,
            "vm_id":instance_id,
            "op":op
        }
        return self.driver._do_action(action, params)
    def get(self, volume_id):
        action = ["volumes","read"]
        params = {
            "volume_id":volume_id
        }
        info=self.driver._do_action(action, params)
        info['uuid']=info['id']
        if info['dev']:
            info['dev']='/dev/'+info['dev']
        return Volume(self, info)
    def list(self):
        action = ["volumes", "list"]
        params = {
            "group_id":self.driver._credential['group_id'],
            "cephpool_id":self.driver._credential['volume_poll_id'],
        }
        vols=[]
        for item in self.driver._do_action(action, params):
            vols.append(Volume(self, item))
        return vols
    def create(self, size, remark=''):
        action = ["volumes","create"]
        params = {
            "group_id":self.driver._credential['group_id'],
            "cephpool_id":self.driver._credential['volume_poll_id'],
            'size':size,
            "remarks":remark
        }
        volume_id=self.driver._do_action(action, params)
        return self.get(volume_id)
    def delete(self, volume_id):
        action = ["volumes","delete"]
        params = {
            "volume_id":volume_id,
        }
        try:
            return self.driver._do_action(action, params)
        except coreapi.exceptions.ErrorMessage as e:
            if 'CEPH\u5757ID\u6709\u8bef' in e.error._data['detail']:
                print('CEPH UUID Mismatch')
                return True
            else:
                raise e
    def mount(self, volume_id, instance_id):
        self._operate_volume(volume_id, instance_id, 'mount')
        return self.get(volume_id)
    def unmount(self, volume_id, instance_id):
        try:
            return self._operate_volume(volume_id, instance_id, 'unmount')
        except coreapi.exceptions.ErrorMessage as e:
            if '\u865a\u62df\u673aUUID\u9519\u8bef' in e.error._data['detail']:
                print('VM UUID Mismatch')
                return True
            else:
                raise e

class Volume(object):
    def __init__(self, manager, info):
        self.manager=manager
        self.id=info['uuid']
        self.size=info['size']
        self.name=info['remarks']
        self.created_at=info['create_time']
        self.attachments=[]
        if info['attach_time']:
            self.attachments.append({'device': info['dev'], 'attached_at': info['attach_time']})