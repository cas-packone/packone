import coreapi
from django.conf import settings
#TODO directly use libvirt and ceph
def do_action(credential, action, params):
    client=coreapi.Client(auth=coreapi.auth.BasicAuthentication(credential['user'], credential['passwd']))
    schema = client.get(credential['api_endpoint'])#TODO improve perf.
    return client.action(schema, action, params=params)

def vm_op(credential, vm_id, op):
    action = ["vms","operations","partial_update"]
    params = {
        "vm_id":vm_id,
        "op":op
    }
    try:
        return do_action(credential, action,params)
    except coreapi.exceptions.ErrorMessage as e:
        if 'not running' in e.error._data['detail'] or 'already running' in e.error._data['detail']:
            print(e.error._data['detail'])
            return True
        else:
            raise e

def vm_status(credential, vm_id):
    action = ["vms","status","list"]
    params = {
        "vm_id":vm_id
    }
    try:
        return int(do_action(credential, action,params))
    except coreapi.exceptions.ErrorMessage as e:
        if '\u865a\u62df\u673aUUID\u9519\u8bef' in e.error._data['detail']:
            print('VM UUID Mismatch')
            return 5
        else:
            raise e

def vm_list(credential, include_remarks=[]):
    include_remarks.append(settings.PACKONE_LABEL)
    action = ["vms", "list"]
    params = {
        "group_id":credential['group_id'],
    }
    result=do_action(credential, action, params)
    vms = list(filter(lambda x: len(set(x['remarks'].split(';')).intersection(set(include_remarks)))==len(include_remarks), result))
    return vms

def vm_read(credential, vm_id):
    action = ["vms","read"]
    params = {
        "vm_id":vm_id
    }
    vm_info=do_action(credential, action, params)
    if not vm_info['remarks'].startswith(settings.PACKONE_LABEL):
        raise Exception('Cannot retrieve non-{} vms!'.format(settings.PACKONE_LABEL))
    else:
        #strip beginning settings.PACKONE_LABEL
        vm_info['remark']=vm_info['remarks'][len(settings.PACKONE_LABEL):]
        return vm_info

def vm_create(credential,image_id,vcpu,mem,template_id=None,remark=''):
    action = ["vms","create"]
    params = {
        "image_id":int(image_id),
        "vcpu":vcpu,
        "mem":mem,
        "group_id":credential['group_id'],
        'vlan_id':credential['vlan_id'],
        "remarks":remark,
    }
    vm_id=do_action(credential, action, params)
    return vm_read(credential, vm_id)

def vm_delete(credential, vm_id):
    action = ["vms","delete"]
    params = {
        "vm_id":vm_id,
    }
    try:
        return do_action(credential, action,params)
    except coreapi.exceptions.ErrorMessage as e:
        if '\u865a\u62df\u673aUUID\u9519\u8bef' in e.error._data['detail']:
            print('VM UUID Mismatch')
            return True
        else:
            raise e

def vm_force_delete(credential, vm_id):
    try:
        vm_op(credential, vm_id, 'poweroff')
    except Exception as e:
        print(e)
    return vm_delete(credential, vm_id)

def volume_op(credential, volume_id, vm_id, op):
    action = ["volumes","vm","partial_update"]
    params = {
        "volume_id":volume_id,
        "vm_id":vm_id,
        "op":op
    }
    return do_action(credential, action, params)

def volume_mount(credential, volume_id, vm_id):
    volume_op(credential, volume_id, vm_id, 'mount')
    return volume_read(credential, volume_id)

def volume_unmount(credential, volume_id, vm_id):
    try:
        return volume_op(credential, volume_id, vm_id, 'unmount')
    except coreapi.exceptions.ErrorMessage as e:
        if '\u865a\u62df\u673aUUID\u9519\u8bef' in e.error._data['detail']:
            print('VM UUID Mismatch')
            return True
        else:
            raise e

def volume_read(credential, volume_id):
    action = ["volumes","read"]
    params = {
        "volume_id":volume_id
    }
    volume_info=do_action(credential, action,params)
    if not volume_info['remarks'].startswith(settings.PACKONE_LABEL):
        raise Exception('Cannot retrieve non-{} volumes!'.format(settings.PACKONE_LABEL))
    else:
        #strip beginning settings.PACKONE_LABEL
        volume_info['remark']=volume_info['remarks'][len(settings.PACKONE_LABEL):]
        volume_info['uuid']=volume_info['id']
        if volume_info['dev']:
            volume_info['dev']='/dev/'+volume_info['dev']
        return volume_info

def volume_create(credential, size, remark=''):
    action = ["volumes","create"]
    params = {
        "group_id":credential['group_id'],
        "cephpool_id":credential['volume_poll_id'],
        'size':size,
        "remarks":remark
    }
    volume_id=do_action(credential, action, params)
    return volume_read(credential, volume_id)

def volume_delete(credential, volume_id):
    action = ["volumes","delete"]
    params = {
        "volume_id":volume_id,
    }
    try:
        return do_action(credential, action, params)
    except coreapi.exceptions.ErrorMessage as e:
        if 'CEPH\u5757ID\u6709\u8bef' in e.error._data['detail']:
            print('CEPH UUID Mismatch')
            return True
        else:
            raise e