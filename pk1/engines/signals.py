from uuid import UUID
import time
from django.db import transaction
from django.db.models import Value as V
from django.db.models.functions import Concat
from django.db.models import Max
from django.utils.timezone import now
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from clouds.signals import materialized, executed, monitored, destroyed, tidied, selected
from clouds.signals import tidy_operation, select_operation
from clouds import utils
from .import models
from clouds.models import Instance, INSTANCE_STATUS, InstanceOperation, INSTANCE_OPERATION, OPERATION_STATUS, Mount, Group, GroupOperation

from django.dispatch import Signal
scaled_out = Signal(providing_args=["instance","name"])

@receiver(scaled_out)
def log(sender,instance,name,**kwargs):
    print('SIGNAL INFO:', sender._meta.app_label, sender._meta.verbose_name, instance, name)

from clouds.models import Cloud, bootstraped

from .utils import remedy_scale_ambari_bootstrap
@receiver(bootstraped, sender=Cloud)
def bootstrap(sender,instance,**kwargs):
    blueprints=list(instance.instanceblueprint_set.filter(name__startswith='packone-bootstap-', public=False))
    s, created=models.Scale.objects.get_or_create(
        name='packone.bootstrap.{}'.format(instance.name),
        _remedy_script=remedy_scale_ambari_bootstrap(),
        owner=instance.owner
    )
    if created: s.init_blueprints.add(*blueprints)
    models.Cluster.objects.get_or_create(name='bootstrap.{}'.format(instance.name), scale=s, owner=instance.owner)

@receiver(post_save, sender=models.Stack)
@receiver(executed, sender=InstanceOperation)
def create_stack(sender,instance,**kwargs):
    if 'created' in kwargs and kwargs['created']:
        instance.host.remedy(instance.driver.init_script+'\n'+'###setup stack end###')
        return
    if instance.operation==INSTANCE_OPERATION.remedy.value and instance.script.endswith('###setup stack end###'):
        instance.target.stack_set.first().import_engine()
    
@receiver(materialized, sender=Group)
@receiver(post_save, sender=models.Cluster)
def scale_out(sender,instance,**kwargs):
    if sender==models.Cluster:
        if not kwargs['created'] or instance.deleting: return
        instance.scale_one_step()
        return
    for cluster in instance.cluster_set.select_for_update():
        cluster.built_time=now()
        cluster.save()
        old_steps=cluster.get_ready_steps().exclude(pk=instance.pk).select_for_update()
        if old_steps.exists():
            old_hosts_script=utils.remedy_script_hosts_add('\n'.join([step.hosts for step in old_steps]))
            new_hosts_script=utils.remedy_script_hosts_add(instance.hosts)   
            #TODO only running remedyless cluster can be scaled-out
            for step in old_steps:
                step.remedy(new_hosts_script)
            instance.remedy(old_hosts_script,manual=False)
            if cluster.scale.remedy_script_scale_out:
                instance.remedy(cluster.scale.remedy_script_scale_out,manual=False)
        elif cluster.scale.remedy_script:
            instance.remedy(cluster.scale.remedy_script,manual=False)
        scaled_out.send(sender=models.Cluster, instance=cluster, name='scaled_out')

@receiver(destroyed, sender=Group)
@transaction.atomic
def scale_in_cluster(sender,instance,**kwargs):
    for cluster in instance.cluster_set.select_for_update():
        cluster.steps.remove(instance)
        if cluster.deleting:
            if not cluster.steps.all().exists():
                destroyed.send(sender=models.Cluster, instance=cluster, name='destroyed')
                cluster.delete()
        else:
            cluster.update_remedy_script(
                utils.remedy_script_hosts_remove(instance.hosts),
                heading=True
            )
            if cluster.scale.remedy_script_scale_in:
                cluster.update_remedy_script(
                    cluster.scale.remedy_script_scale_in,
                    heading=True
                )

@receiver(monitored, sender=Group)
@receiver(tidied, sender=models.ClusterOperation)
@receiver(executed, sender=models.ClusterOperation)
def monitor_status(sender, instance, **kwargs):
    if sender==Group:
        if instance.deleting: return
        for cluster in instance.cluster_set.all():
            status=cluster.steps.all().aggregate(Max('status'))['status__max']
            models.Cluster.objects.filter(pk=cluster.pk).update(status=status)
            cluster.refresh_from_db()
            monitored.send(sender=models.Cluster, instance=cluster, name='monitored')
    else:
        if instance.status==OPERATION_STATUS.waiting.value: return
        else:
            instance.target.monitor()

post_save.connect(tidy_operation,sender=models.ClusterOperation)
monitored.connect(select_operation,sender=models.Cluster)
@receiver(selected, sender=models.ClusterOperation)
def execute_operation(sender,instance,**kwargs):
    instance.execute()

#TODO use threading join to reduce last singal check
@receiver(executed, sender=GroupOperation)
@transaction.atomic
def close_cluster_operation(sender, instance, **kwargs):
    for running_op in models.ClusterOperation.objects.select_for_update().filter(
        batch_uuid=instance.batch_uuid,
        started_time__isnull=False
    ):
        if not running_op.get_remain_oprations().exists():
            running_op.completed_time=now()
            running_op.status=running_op.get_status()
            running_op.save()
            executed.send(sender=models.ClusterOperation, instance=running_op, name='executed')

        # elif instance.operation==models.COMPONENT_OPERATION.stop.value:
        #     print(instance.target.stop())
        # elif instance.operation==models.COMPONENT_OPERATION.restart.value:
        #     raise Exception('not implemented yet')
        # else:
        #     raise Exception('illegal operation')
        # instance.completed_time=now()

@receiver(post_delete, sender=GroupOperation)
def purge_cluster_operation(sender, instance, **kwargs):
    c_op=models.ClusterOperation.objects.filter(batch_uuid=instance.batch_uuid).first()
    if c_op and not c_op.get_sub_operations().exists():
        c_op.delete()

# @receiver(post_save, sender=models.EngineOperation)
# def operate_engine(sender,instance,created,**kwargs):
#     if created:
#         if not instance.engine.enabled:
#             raise Exception('cannot operate disabled engine')
#         if instance.operation==models.COMPONENT_OPERATION.start.value:
#             instance.engine.start(instance.pilot)
#         elif instance.operation==models.COMPONENT_OPERATION.stop.value:
#             instance.engine.stop(instance.pilot)
#         instance.completed_time=now()
#         instance.save()