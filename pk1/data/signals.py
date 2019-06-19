
from django.dispatch import receiver
from django.db.models.signals import pre_save,post_save,pre_delete,post_delete,m2m_changed
from .import models
import datetime
from django.db import transaction
from multiprocessing.pool import ThreadPool
from threading import Thread
from clouds import utils
from clouds.signals import materialized, executed, monitored, destroyed, tidied, selected
from clouds.signals import tidy_operation, select_operation, executed
from clouds.models import InstanceOperation

loading_instance_operations={}

@receiver(post_save, sender=models.DataInstance)
def materialize_data_instance(sender,instance,**kwargs):
    if not kwargs['created'] or instance.ready: return
    tmpdir="/data/packone/"+instance.uri_suffix
    scripts="mkdir -p "+tmpdir+' && cd '+tmpdir+'\n'
    scripts+=instance.dataset.remedy_script.format(dataset=instance.dataset, instance=instance)+'\n\n'
    io=instance.entry_host.remedy(scripts)
    loading_instance_operations[io.pk]=instance.pk

@receiver(executed, sender=InstanceOperation)
@transaction.atomic
def update_data_instance_status(sender,instance,**kwargs):
    if instance.pk not in loading_instance_operations: return
    for di in models.DataInstance.objects.filter(pk=loading_instance_operations[instance.pk]).select_for_update():
        del loading_instance_operations[instance.pk]
        di.built_time=datetime.datetime.now()
        di.status=models.COMPONENT_STATUS.active.value
        di.save()

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