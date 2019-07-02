from novaclient import client
from novaclient.exceptions import NotFound
from cinderclient import client as cinder_client
from uuid import uuid4
import time
from django.conf import settings
from ..models import INSTANCE_STATUS

def get_nova(credential):#TODO opt perf.
    return client.Client(credential['api_version'], username=credential['username'], password=credential['password'], project_name=credential['project_name'], auth_url=credential['auth_url'])

def get_cinder(credential):#TODO opt perf.
    return cinder_client.Client(credential['api_version'],credential['username'],credential['password'],credential['project_name'],auth_url=credential['auth_url'])

def vm_op(credential, vm_id, op):
    nova=get_nova(credential)
    vm=nova.servers.get(vm_id)
    if op=='start':
        return vm.start()
    elif op=='reboot':
        return vm.reboot()
    elif op=='shutdown' or op=='poweroff':
        return vm.stop()
    else:
        raise Exception('Invalid VM Operation: {}'.format(op))

def vm_vnc_url(credential, vm_id):
    nova=get_nova(credential)
    vm=nova.servers.get(vm_id)
    return vm.get_vnc_console('novnc')['console']['url']

def vm_list(credential, include_remarks=[]):
    nova = get_nova(credential)
    return nova.servers.list()

def vm_read(nova, server):
    if not server.name.startswith(settings.PACKONE_LABEL):
        raise Exception('Cannot retrieve non-{} vms!'.format(settings.PACKONE_LABEL))
    flavor=nova.flavors.get(server.flavor['id'])
    return {
        'uuid':server.id,
        'create_time':server.created,
        'ipv4':server.addresses['provider'][0]['addr'],
        'remark':server.name,
        'vcpu':flavor.vcpus,
        'mem':flavor.ram,
    }

def vm_create(credential,image_id,vcpu,mem,template_id=None,remark=''):
    nova=get_nova(credential)
    vm=nova.servers.create(
        name=remark,
        image=image_id,
        flavor=template_id,
        security_groups=[credential['security_group']],
        nics=[{'net-id':credential['net-id']}],
        key_name=credential['key_name']
    )
    mustend = time.time() + 600
    while time.time() < mustend:
        vm=nova.servers.get(vm.id)
        if 'provider' in vm.addresses: break
        time.sleep(5)
    vm.stop()
    return vm_read(nova,vm)

def vm_delete(credential, vm_id):
    nova=get_nova(credential)
    try:
        return nova.servers.delete(vm_id)
    except NotFound as e:
        print(e)

def vm_force_delete(credential, vm_id):
    return vm_delete(credential, vm_id)

def volume_mount(credential, volume_id, vm_id):
    nova=get_nova(credential)
    nova.volumes.create_server_volume(server_id=vm_id,volume_id=volume_id)
    cinder=get_cinder(credential)
    volume=cinder.volumes.get(volume_id)
    mustend = time.time() + 60
    while time.time() < mustend:
        volume=cinder.volumes.get(volume.id)
        if volume.status == 'in-use': break
        time.sleep(1)
    return volume_read(credential,volume.id)

def volume_unmount(credential, volume_id, vm_id):
    nova=get_nova(credential)
    mustend = time.time() + 60
    while time.time() < mustend:
        vm=nova.servers.get(vm_id)
        if vm.status == 'SHUTOFF': break
        time.sleep(1)
    return nova.volumes.delete_server_volume(server_id=vm_id,volume_id=volume_id)

def volume_read(credential,volume_id):
    cinder=get_cinder(credential)
    volume=cinder.volumes.get(volume_id)
    if not volume.name.startswith(settings.PACKONE_LABEL):
        raise Exception('Cannot retrieve non-{} volumes!'.format(settings.PACKONE_LABEL))
    dev=None
    attach_time=None
    if volume.attachments:
        dev=volume.attachments[0]['device']
        attach_time=volume.attachments[0]['attached_at']
    return {
        'remark':volume.name,
        'uuid':volume.id,
        'create_time':volume.created_at,
        'dev':dev,
        'attach_time':attach_time
    }

def volume_create(credential, size, remark=''):
    cinder=get_cinder(credential)
    volume=cinder.volumes.create(
        name=remark,
        size=size
    )
    mustend = time.time() + 60
    while time.time() < mustend:
        volume=cinder.volumes.get(volume.id)
        if volume.status == 'available': break
        time.sleep(1)
    return volume_read(credential,volume.id)

def volume_delete(credential, volume_id):
    cinder=get_cinder(credential)
    mustend = time.time() + 60
    volume=cinder.volumes.get(volume_id)
    while time.time() < mustend:
        if volume.status == 'available': break
        time.sleep(1)
        volume=cinder.volumes.get(volume_id)
    return volume.delete()

def vm_status(credential, vm_id):
    nova=get_nova(credential)
    vm=nova.servers.get(vm_id)
    if vm.status=='ACTIVE':
        return INSTANCE_STATUS.active.value
    elif vm.status=='PAUSED':
        return INSTANCE_STATUS.pause.value
    elif vm.status=='BUILDING':
        return INSTANCE_STATUS.preparing.value
    elif vm.status=='STOPPED':
        return INSTANCE_STATUS.shutdown.value
    elif vm.status=='SHUTOFF':
        return INSTANCE_STATUS.shutdown.value
    elif vm.status=='ERROR':
        return INSTANCE_STATUS.failure.value
    return INSTANCE_STATUS.null.value

def image_list(credential):
    nova = get_nova(credential)
    images=[]
    for image in nova.glance.list():
        images.append({
            'id':image.id,
            'name':image.name,
        })
    return images

def template_list(credential):
    nova = get_nova(credential)
    templates=[]
    for f in nova.flavors.list():
        templates.append({
            'id':f.id,
            'name':f.name,
            'mem':f.ram,
            'vcpu':f.vcpus
        })
    return templates