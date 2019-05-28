
from django.dispatch import receiver
from django.db.models.signals import pre_save,post_save,pre_delete,post_delete,m2m_changed
from .import models
import datetime
from django.db import transaction
from multiprocessing.pool import ThreadPool
from threading import Thread
from clouds import utils
from clouds.signals import materialized, executed, monitored, destroyed, tidied, selected
from clouds.signals import tidy_operation, select_operation


@receiver(post_save, sender=models.DataInstance)
def materialize_data_instance(sender,instance,**kwargs):
    if not kwargs['created'] or instance.ready: return
    # (host,cmd,path)=instance.uri_elected.split('://')
    # ins=instance.cluster.find_instance(host)
    # if not ins: raise Exception('cannot find the uri located instance: {}'.format(host))
    # ssh=utils.open_ssh(ins.ipv4,ins.location.instance_credential)
    # tmpdir="/data/space/"+instance.uri_suffix
    # utils.exec_batch(ssh,"mkdir -p "+tmpdir)
    # cmd='cd '+tmpdir+';'+instance.dataset.uri+";"
    # if instance.dataset.remedy_script: cmd+=instance.dataset.remedy_script
    # utils.exec_batch(ssh,cmd)
    # utils.exec_batch(ssh,'cd '+tmpdir+';'+instance.engine.remedy_script.format(tmpdir))
    # ssh.close()
    # instance.created_time=datetime.datetime.now()
    # instance.save()

@receiver(materialized, sender=models.DataInstance)
@receiver(tidied, sender=models.DataInstanceOperation)
@receiver(executed, sender=models.DataInstanceOperation)
def monitor_data_instance(sender, instance, **kwargs):
    if sender==models.DataInstanceOperation:
        if instance.status==models.OPERATION_STATUS.waiting.value: return
    #     instance=instance.target
    # if not instance.ready: return
    # Thread(target=instance.monitor).start()

post_save.connect(tidy_operation,sender=models.DataInstanceOperation)
monitored.connect(select_operation,sender=models.DataInstance)
@receiver(selected, sender=models.DataInstanceOperation)
def execute_operation(sender,instance,**kwargs):
    instance.execute()