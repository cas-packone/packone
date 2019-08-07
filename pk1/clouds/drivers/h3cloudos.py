import requests
import time
import json
import re
import logging, os, sys

class Driver(object):
    def __init__(self, cloud):
        self.log = logging.getLogger(os.path.basename(__file__).split('.')[0].upper())
        if not len(self.log.handlers): #prevent to add duplicated handlers
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
        self.project_id=requests.get(url=self.endpoint+'/v3/projects?name='+self._credential['project_name'], headers=self._headers).json()['projects'][0]['id']
        self.tenant_endpoint='/v2/'+self.project_id
        self.instances=InstanceManager(self)
        self.volumes=VolumeManager(self)
        self.images=ImageManager(self)
        self.flavors=FlavorManager(self)
        self.keypairs=KeyManager()
    def _request(self,url,method=requests.get,data=None,retry_when_response_unexpected_strings=None,retry_until_response_expected_strings=None):
        mustend = time.time() + 900
        while time.time() < mustend:
            res = method(self.endpoint+url,headers=self._headers,data=json.dumps(data))
            self.log.info('REQUEST: token/{}, {} {}, status/{}'.format(self._token, method.__name__, url, res.status_code))
            if retry_when_response_unexpected_strings:
                ss=list(filter(lambda x: x in res.text, retry_when_response_unexpected_strings))
                if ss:
                    self.log.info('REQUEST RETRING, AS UNEXPECTED RESPONSE STRING "{}" appeared in response: "{}"!'.format(ss[0], res.text))
                    time.sleep(5)
                    continue
            if retry_until_response_expected_strings:
                ss=list(filter(lambda x: x in res.text, retry_until_response_expected_strings))
                if not ss:
                    self.log.info('REQUEST RETRING, AS EXPECTED RESPONSE STRING "{}"  didn\'t appear in response: "{}"!'.format(' or '.join(retry_until_response_expected_strings), res.text))
                    time.sleep(5)
                    continue
            break
        if not res.ok:
            raise Exception(res.status_code, res.text)
        try:
            if res.text: return res.json()
        except Exception as e:
            print(type(e), e)
    def _get(self, url, retry_when_response_unexpected_strings=None, retry_until_response_expected_strings=None):
        return self._request(url,retry_when_response_unexpected_strings=retry_when_response_unexpected_strings, retry_until_response_expected_strings=retry_until_response_expected_strings)
    def _tenant_get(self, url, retry_when_response_unexpected_strings=None, retry_until_response_expected_strings=None):
        return self._request(self.tenant_endpoint+url, retry_when_response_unexpected_strings=retry_when_response_unexpected_strings, retry_until_response_expected_strings=retry_until_response_expected_strings)
    def _create(self, url, data, retry_when_response_unexpected_strings=None, retry_until_response_expected_strings=None):
        return self._request(url,method=requests.post,data=data,retry_when_response_unexpected_strings=retry_when_response_unexpected_strings, retry_until_response_expected_strings=retry_until_response_expected_strings)
    def _tenant_create(self, url, data, retry_when_response_unexpected_strings=None, retry_until_response_expected_strings=None):
        return self._create(self.tenant_endpoint+url,data=data,retry_when_response_unexpected_strings=retry_when_response_unexpected_strings, retry_until_response_expected_strings=retry_until_response_expected_strings)
    def _delete(self, url, retry_when_response_unexpected_strings=None, retry_until_response_expected_strings=None):
        return self._request(url,method=requests.delete,retry_when_response_unexpected_strings=retry_when_response_unexpected_strings, retry_until_response_expected_strings=retry_until_response_expected_strings)
    def _tenant_delete(self, url, retry_when_response_unexpected_strings=None, retry_until_response_expected_strings=None):
        return self._delete(self.tenant_endpoint+url,retry_when_response_unexpected_strings=retry_when_response_unexpected_strings, retry_until_response_expected_strings=retry_until_response_expected_strings)

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
        info=self.driver._get('/v2/images/'+id)['image']
        return Image(info)
    def list(self):
        images=[]
        for item in self.driver._get('/v2/images')['images']:
            images.append(Image(item))
        return images
    def delete(self, id):
        return self.driver._delete('/v2/images/'+id)

class Image(object):
    def __init__(self, info):
        self.info=info
        self.id=info['id']
        self.name=info['name']
        self.created_at=info['created_at']
    def __repr__(self):
        return '{}: {}'.format(type(self).__name__, self.name)

class InstanceManager(object):
    mountable_status=['ACTIVE','SHUTDOWN']
    def __init__(self, driver):
        self.driver=driver
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
        		"name": re.sub(r'[\W,_]', '-', remark).strip('-'),
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
        info=self.driver._tenant_create('/servers',data=data, retry_when_response_unexpected_strings=['is not active'])['server']
        info=self.driver._tenant_get('/servers/'+info['id'],retry_until_response_expected_strings=['ACTIVE'])['server']
        ins=Instance(self, info)
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
    def get_console_url(self, type):
        return self.manager.driver._tenant_create('/servers/{}/action'.format(self.id), data={"os-getVNCConsole": { "type": type}})
    def create_image(self, image_name):
        self.manager.driver._tenant_create('/servers/{}/action'.format(self.id), data={"createImage":{"name":image_name,"metadata":{"operator_id":self.manager.driver.project_id}}},retry_when_response_unexpected_strings=['conflictingRequest'])
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
        info=self.driver._tenant_get('/volumes/'+info['id'], retry_until_response_expected_strings=['available'])['volume']
        return Volume(self, info)
    def delete(self, id):
        self.driver._tenant_get('/volumes/'+id, retry_until_response_expected_strings = ['available', 'error'])['volume']
        return self.driver._tenant_delete('/volumes/'+id)
    def mount(self, volume_id, instance_id):
        data={"volumeAttachment": {"volumeId": volume_id}}
        self.driver._tenant_create('/servers/'+instance_id+'/os-volume_attachments',data=data)
        info = self.driver._tenant_get('/volumes/'+volume_id,retry_until_response_expected_strings=['in-use'])['volume']
        return Volume(self, info)
    def unmount(self, volume_id, instance_id):
        self.driver._tenant_get('/servers/'+instance_id,retry_until_response_expected_strings=['SHUTOFF'])
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