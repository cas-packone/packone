import paramiko
from scp import SCPClient
from django.conf import settings
import json
from io import StringIO
import calendar
import time
from django.urls import reverse
from django.utils.html import format_html

def get_url(obj):
    label= obj.name if getattr(obj,'name',False) else str(obj)
    url=reverse('admin:{}_{}_change'.format(obj._meta.app_label,obj._meta.model_name),args=(obj.pk,))
    return '<a href='+url+'>'+label+'</a>'

def get_formated_url(obj):
    return format_html(get_url(obj))

def get_current_timestamp():
    ts = calendar.timegm(time.gmtime())
    return ts

def get_refer_GET_parameter(request,name=None):
    from urllib import parse
    params=parse.parse_qs(parse.urlparse(request.META['HTTP_REFERER']).query)
    if not name:
        return params
    if name in params:
        return params[name][0]
    return None

def remedy_script_tidy(script, supervisor_operations):
    stats=[s.rstrip() for s in script.split('\n')]
    begin_i=0
    current_i=0
    length=len(stats)
    operations=[]
    while current_i < length:
        if not stats[current_i] or stats[current_i] in supervisor_operations:
            if current_i>begin_i:
                operations.append('\n'.join(stats[begin_i:current_i]))
            if stats[current_i]:
                operations.append(stats[current_i])  
            begin_i=current_i+1
        elif current_i==length-1:
            operations.append('\n'.join(stats[begin_i:current_i+1]))
        current_i+=1
    return operations

def remedy_script_hosts_add(hosts,overwrite=False):
    if overwrite: return "echo '{hosts}' >/etc/hosts".format(hosts=hosts)
    return "echo '{hosts}' >>/etc/hosts".format(hosts=hosts)

#TODO only support linux
def remedy_script_hosts_remove(hosts):
    return ';'.join(["sed -i '/{}/d' /etc/hosts".format(h) for h in hosts.split('\n') if h])
#TODO only support linux
def remedy_script_hosts_remove_from(tag):
    return "sed -i '/{}/,$d' /etc/hosts".format(tag)
#TODO only support linux
def remedy_script_hostname(hostname):
    return "hostnamectl set-hostname {hostname}".format(hostname=hostname)

#TODO make filesystem type chooseable
#must use rsync -ax to keep permissions
def remedy_script_mount_add(mount):
    return "mkfs.xfs {mount.dev}>/dev/null 2>&1 && " \
    "rsync -ax {mount.point} {mount.point}.old>/dev/null 2>&1 && " \
    "mkdir -p {mount.point} && " \
    "mount {mount.dev} {mount.point} && " \
    "rsync -ax {mount.point}.old/* {mount.point}>/dev/null 2>&1 && " \
    "rm -rf {mount.point}.old/ && " \
    "echo '{mount.dev} {mount.point} xfs defaults 0 2'>>/etc/fstab". \
    format(mount=mount)

def remedy_script_mount_remove(mount):
    return "sed -i '/{}/d' /etc/fstab".format('{mount.dev} {mount.point}'.format(mount=mount).replace('/', '\/'))

def remedy_image_ambari_agent():
    return 'wget -q https://public-repo-1.hortonworks.com/ambari/centos7/2.x/updates/2.7.3.0/ambari.repo -O /etc/yum.repos.d/ambari.repo\n\nyum -qy install ambari-agent >/dev/null 2>&1'

def remedy_image_ambari_server():
    return 'yum -qy install ambari-server >/dev/null 2>&1\n\n' \
        'ambari-server setup -s >/dev/null\n\n' \
        'ambari-server start'

def remedy_scale_ambari_bootstrap():
    return "sed -i 's/hostname=localhost/hostname=master1.packone/g' /etc/ambari-agent/conf/ambari-agent.ini\n\n" \
        "ambari-agent start >/dev/null 2>&1\n\n" \
        'if [ `hostname` == "master1.packone" ]; then\n' \
        'sleep 10\n' \
        'pip install ambari\n' \
        'ambari localhost:8080 cluster create packone typical_triple master1.packone master2.packone slave.packone\n' \
        "fi"

class SSH:
    def __init__(self,host,credential):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        credential=credential
        if 'password' not in credential:
            credential['password'] = None
        if 'port' not in credential:
            credential['port'] = 22
        if 'private_key' in credential:
            private_key_file=StringIO(credential['private_key'])
            credential['pkey']=paramiko.RSAKey.from_private_key(private_key_file)
            private_key_file.close()
        else:
            credential['pkey']=None
        mustend = time.time() + 90
        e=Exception()
        while time.time() < mustend:
            time.sleep(1)
            try:
                self.client.connect(
                    host,
                    username=credential['username'],
                    password=credential['password'],
                    pkey=credential['pkey'],
                    port=credential['port'],
                    timeout=None
                )
            except Exception as ex:
                e=ex
            else:
                return
        raise e

    def exec_batch(self, cmd):
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
        except paramiko.SSHException as e:
            err='EXCEPTION MESSAGE:\n'+str(e)
            out=''
        else:
            err='\n'.join(stderr.readlines())
            if err: err='STDERR:\n'+err
            out='STDOUT:\n'+'\n'.join(stdout.readlines())
        finally:
            return out, err

    def close(self):
        self.client.close()