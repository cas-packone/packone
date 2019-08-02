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
    return "mkfs.xfs {mount.dev}>/dev/null 2>&1\n" \
    "rsync -ax {mount.point} {mount.point}.old>/dev/null 2>&1\n" \
    "mkdir -p {mount.point}\n" \
    "mount {mount.dev} {mount.point}\n" \
    "rsync -ax {mount.point}.old/* {mount.point}>/dev/null 2>&1\n" \
    "rm -rf {mount.point}.old/\n" \
    "echo '{mount.dev} {mount.point} xfs defaults 0 2'>>/etc/fstab". \
    format(mount=mount)

def remedy_script_mount_remove(mount):
    return "sed -i '/{}/d' /etc/fstab".format('{mount.dev} {mount.point}'.format(mount=mount).replace('/', '\/'))

def remedy_image_ambari_agent():
    return 'curl -Ssl https://public-repo-1.hortonworks.com/ambari/centos7/2.x/updates/2.7.3.0/ambari.repo -o /etc/yum.repos.d/ambari.repo\n\nyum -q -y install ambari-agent 2>&1'

def remedy_image_ambari_server():
    return 'yum -q -y install ambari-server 2>&1\n\n' \
        'ambari-server setup -s >/dev/null\n\n' \
        'ambari-server start'

from paramiko import RSAKey
def gen_ssh_key():
    key=RSAKey.generate(2048)
    private_key_file=StringIO()
    key.write_private_key(private_key_file)
    pri=private_key_file.getvalue()
    private_key_file.close()
    pub=key.get_base64()
    pub='ssh-rsa '+pub
    return pub, pri

def get_pub_key(private_key):
    private_key_file=StringIO(private_key)
    key=paramiko.RSAKey.from_private_key(private_key_file)
    private_key_file.close()
    pub=key.get_base64()
    pub='ssh-rsa '+pub
    return pub

class SSH:
    def __init__(self,host,username='root',password=None,private_key=None,port=None):
        self.username=username
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if private_key:
            private_key_file=StringIO(private_key)
            private_key=paramiko.RSAKey.from_private_key(private_key_file)
            private_key_file.close()
        mustend = time.time() + 600
        e=Exception()
        while time.time() < mustend:
            time.sleep(5)
            try:
                self.client.connect(
                    host,
                    username=username,
                    password=password,
                    pkey=private_key,
                    timeout=None
                )
            # except paramiko.AuthenticationException as ex:
            #     raise ex
            except paramiko.ssh_exception.NoValidConnectionsError as ex:
                continue
            except Exception as ex:
                # import traceback
                # traceback.print_tb(ex.__traceback__)
                print(ex)
                e=ex
                continue
            else:
                return
        raise e

    def exec_batch(self, cmd):
        ftp = self.client.open_sftp()
        file=ftp.file('/tmp/packone.bash', "w", -1)
        file.write(cmd)
        file.flush()
        ftp.close()
        cmd='sudo -uroot ' if self.username!='root' else ''
        cmd+='bash /tmp/packone.bash'
        stdin, stdout, stderr = self.client.exec_command(cmd)
        err='\n'.join(stderr.readlines())
        if err: err='STDERR:\n'+err
        out='STDOUT:\n'+'\n'.join(stdout.readlines())
        if out.find('ERROR: Exiting with exit code 1')!=-1:
            err+=out
            out=''
        return out, err

    def close(self):
        self.client.close()