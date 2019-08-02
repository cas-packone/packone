import requests
import time
import json
import logging, os, sys

class Driver(object):
    def __init__(self, cloud):
        self.log = logging.getLogger(os.path.basename(__file__).split('.')[0].upper())
        self.log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.log.addHandler(ch)
        self._cloud=cloud
        self._credential=cloud.platform_credential
        self._headers={'Content-Type': 'application/json'}
        self.endpoint=self._credential['endpoint']
        token=requests.post(
            url=self.endpoint+'/v3/auth/tokens',
            headers=self._headers,
            data=json.dumps({
                "auth":{
                    "identity": {
                        "methods": ["password"],
                        "password": {"user": {"domain": {"id": "default"},"name": self._credential['username'],"password": self._credential['password']}}
                    },
                    "scope": {
                        "project": {"domain": {"id": "default"},"name": self._credential['project_name']}
                    }
                }
            })
        ).headers['X-Subject-Token']
        self._token=token
        self._headers['X-Auth-Token']=token
        project_id=requests.get(url=self.endpoint+'/v3/projects?name='+self._credential['project_name'], headers=self._headers).json()['projects'][0]['id']
        self.tenant_endpoint='/v2/'+project_id
        self.instances=InstanceManager(self)
        self.volumes=VolumeManager(self)
        self.images=ImageManager(self)
        self.flavors=FlavorManager(self)
        self.keypairs=KeyManager()
    def _request(self,url,method=requests.get,data=None):
        res = method(self.endpoint+url,headers=self._headers,data=json.dumps(data))
        self.log.info('REQUEST: token/{}, {} {}, status/{}'.format(self._token, method.__name__, url, res.status_code))
        if not res.ok:
            raise Exception(res.status_code, res.text)
        try:
            if res.text: return res.json()
        except Exception as e:
            print(type(e), e)
    def _get(self, url):
        return self._request(url)
    def _tenant_get(self, url):
        return self._request(self.tenant_endpoint+url)
    def _create(self, url, data):
        return self._request(url,method=requests.post,data=data)
    def _tenant_create(self, url, data):
        return self._create(self.tenant_endpoint+url,data=data)
    def _delete(self, url):
        return self._request(url,method=requests.delete)
    def _tenant_delete(self, url):
        return self._delete(self.tenant_endpoint+url)

class KeyManager(object):
    def create(self, name, public_key):
        return None
    def delete(self, name, public_key):
        return None

class FlavorManager(object):
    def __init__(self, driver):
        self.driver=driver
    def get(self, id):
        for tpl in self.list():
            if tpl.id==id:
                return tpl
        raise Exception('unfounded flavor (id: {})!'.format(id))
    def list(self):
        flavors=[]
        for item in self.driver._tenant_get('/flavors/detail')['flavors']:
            flavors.append(Flavor(item))
        return flavors
 
class Flavor(object):
    def __init__(self, info):
        self.info=info
        self.id=info['id']
        self.name=info['name']
        self.ram=info['ram']
        self.vcpus=info['vcpus']
    def __repr__(self):
        return '{}: {}'.format(type(self).__name__, self.name)

class ImageManager(object):
    def __init__(self, driver):
        self.driver=driver
    def get(self, id):
        info=self.driver._tenant_get('/images/'+id)['image']
        return Image(info)
    def list(self):
        images=[]
        for item in self.driver._tenant_get('/images')['images']:
            images.append(Image(item))
        return images
    def delete(self, id):
        return self.driver._delete('/v2/images/'+id)

class Image(object):
    def __init__(self, info):
        self.info=info
        self.id=info['id']
        self.name=info['name']
        from django.utils.timezone import now
        self.created_at=now()
    def __repr__(self):
        return '{}: {}'.format(type(self).__name__, self.name)

class InstanceManager(object):
    def __init__(self, driver):
        self.driver=driver
        self.mountable_status=['ACTIVE','SHUTDOWN']
    def get(self, id):
        info=self.driver._tenant_get('/servers/'+id)['server']
        return Instance(self, info)
    def list(self):
        inss=[]
        for item in self.driver._tenant_get('/servers/detail')['servers']:
            inss.append(Instance(self, item))
        return inss
    def create(self, image_id, template_id, remark='packone', **kwargs):
        data={
        	"server": {
        		"name": remark.replace(';', '.'),
        		"imageRef": image_id,
        		"flavorRef": template_id,
                "availability_zone": self.driver._credential["nova-availability_zone"],
        		"networks": [
        			{
        				"uuid": self.driver._credential['net-id']
        			}
        		]
        	}
        }
        info=self.driver._tenant_create('/servers',data=data)['server']
        ins = self.get(info['id'])
        mustend = time.time() + 600
        while time.time() < mustend:
            if 'provider' in ins.addresses:
                break
            time.sleep(5)
            ins=self.get(ins.id)
        from ..utils import SSH
        ssh=SSH(ins.addresses['provider'][0]['addr'],'root',password=info['adminPass'])
        pub=self.driver._cloud._public_key
        ssh.exec_batch('HM=~{}; cd $HM; mkdir -p .ssh; cd .ssh; echo "{}">>authorized_keys; chmod 400 authorized_keys'.format(self.driver._cloud.instance_credential_username, pub))
        ssh.close()
        return ins
    def delete(self, id):
        try:
            return self.driver._tenant_delete('/servers/'+id)
        except Exception as e:
            print(e)
    def force_delete(self, id):
        return self.delete(id)
    def get_status(self, id):
        return self.get(id).status

class Instance(object):
    def __init__(self, manager, info):
        self.info=info
        self.manager=manager
        self.id=info['id']
        self.addresses={}
        for addr in info['addresses']:
            self.addresses['provider']=info['addresses'][addr] #TODO remove 'provider' key
            break
        self.name=info['name']
        self.status=info['status']
        self.created=info['created']
    def __repr__(self):
        return '{}: {}-{}'.format(type(self).__name__, self.name, self.addresses['provider'][0]['addr'] if 'provider' in self.addresses else self.addresses)
    def get_console_url(self):
        return self.manager.driver._tenant_create('/servers/{}/action'.format(self.id), data={"os-getVNCConsole": { "type": "novnc"}})
    def create_image(self, image_name):
        return self.manager.driver._tenant_create('/servers/{}/action'.format(self.id), data={"createImage":{"name":image_name}})
    def start(self):
        return self.manager.driver._tenant_create('/servers/{}/action'.format(self.id), data={"os-start": None})
    def reboot(self):
        return self.manager.driver._tenant_create('/servers/{}/action'.format(self.id), data={"reboot": {"type": "SOFT"}})
    def stop(self):
        return self.manager.driver._tenant_create('/servers/{}/action'.format(self.id), data={"os-stop": None})

class VolumeManager(object):
    def __init__(self, driver):
        self.driver=driver
    def get(self, id):
        info=self.driver._tenant_get('/volumes/'+id)['volume']
        return Volume(self, info)
    def list(self):
        vols=[]
        for item in self.driver._tenant_get('/volumes/detail')['volumes']:
            vols.append(Volume(self, item))
        return vols
    def create(self, size, remark='packone'):
        data={"volume": {"name": remark,"size": size, 'availability_zone': self.driver._credential['cinder-availability_zone']}}
        info=self.driver._tenant_create('/volumes',data=data)['volume']
        vol = self.get(info['id'])
        mustend = time.time() + 60
        while time.time() < mustend:
            if vol.status == 'available': break
            time.sleep(5)
            vol = self.get(vol.id)
        return vol
    def delete(self, id):
        mustend = time.time() + 60
        while time.time() < mustend:
            try:
                volume=self.get(id)
            except Exception as e:
                print(e)
                return
            if volume.status in ['available', 'error']: break
            time.sleep(5)
        return self.driver._tenant_delete('/volumes/'+id)
    def mount(self, volume_id, instance_id):
        data={"volumeAttachment": {"volumeId": volume_id}}
        self.driver._tenant_create('/servers/'+instance_id+'/os-volume_attachments',data=data)
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
        return self.driver._tenant_delete('/servers/'+instance_id+'/os-volume_attachments/'+volume_id)

class Volume(object):
    def __init__(self, manager, info):
        self.info=info
        self.manager=manager
        self.id=info['id']
        self.size=info['size']
        self.name=info['name']
        self.created_at=info['created_at']
        self.attachments=info['attachments']
        self.status=info['status']
    def __repr__(self):
        return '{}: {}-{} GB'.format(type(self).__name__, self.name, self.size)