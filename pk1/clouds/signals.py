import traceback
from uuid import UUID
from threading import Thread
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils.timezone import now
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from .models import Cloud, Image, Instance, Volume, Mount, InstanceOperation, Group, GroupOperation
from .models import INSTANCE_OPERATION, OPERATION_STATUS, VOLUME_STATUS
from . import utils

from django.dispatch import Signal
materialized = Signal(providing_args=["instance","name"])
destroyed = Signal(providing_args=["instance","name"])
tidied = Signal(providing_args=["instance","name"])
selected = Signal(providing_args=["instance","name"])
from .models import monitored
from .models import executed

@receiver(materialized)
@receiver(destroyed)
@receiver(monitored)
@receiver(tidied)
@receiver(selected)
@receiver(executed)
def log(sender,instance,name,**kwargs):
    print('SIGNAL INFO:', sender._meta.app_label, sender._meta.verbose_name, instance, name)

@receiver(post_save, sender=Cloud)
def import_image(sender,instance,**kwargs):
    if kwargs['created']:
        instance.import_image()
        instance.import_template()
        
@receiver(post_save, sender=Image)
def clone_image(sender,instance,**kwargs):
    if not instance.parent: return
    if instance.parent.access_id != instance.access_id:
        raise Exception('Must keep access_id same with parent')
    if instance.parent.cloud != instance.cloud:
        raise Exception('Must keep cloud same with parent')

# actions relies on status must be registered to the monitored signal first.
@receiver(materialized, sender=Instance)
@receiver(post_save, sender=Mount)
@receiver(tidied, sender=InstanceOperation)
@receiver(executed, sender=InstanceOperation)
def monitor_instance(sender, instance, **kwargs):
    if sender==Mount:
        if not kwargs['created'] or instance.ready: return
        instance=instance.instance
    if sender==InstanceOperation:
        if instance.status==OPERATION_STATUS.waiting.value: return
        instance=instance.target
    if not instance.ready: return
    Thread(target=instance.monitor).start()

@receiver(post_save, sender=Instance)
def materialize_instance(sender, instance, **kwargs):
    if not kwargs['created'] or instance.ready: return
    instance.built_time=now()
    instance.save()
    instance.update_remedy_script(instance.template.remedy_script+'\n'+instance.image.remedy_script)
    @transaction.atomic
    def materialize(instance=instance):
        instance=sender.objects.select_for_update().get(pk=instance.pk)
        remark = settings.PACKONE_LABEL+'.'+instance.cloud.name+';'
        if instance.remark: remark+=instance.remark
        info=instance.cloud.driver.vm_create(
            instance.cloud.platform_credential,
            instance.image.access_id,
            instance.template.vcpu,
            instance.template.mem,
            instance.template.access_id,
            remark
        )
        instance.uuid=UUID(info["uuid"].replace('-', ''), version=4)
        instance.vcpu=info["vcpu"]
        instance.mem=info["mem"]
        instance.built_time=info["create_time"]
        instance.ipv4=info["ipv4"]
        instance.save()
        hosts='###instance###\n'+instance.hosts_record
        if instance.cloud.hosts: hosts=hosts+'\n###cloud###\n'+instance.cloud.hosts
        instance.update_remedy_script(utils.remedy_script_hosts_add(hosts, overwrite=True),heading=True)
        materialized.send(sender=sender, instance=instance, name='materialized')
    transaction.on_commit(Thread(target=materialize).start)

@receiver(pre_save, sender=Instance)
def update_instance_hostname(sender, instance, **kwargs):
    if not instance.pk:
        if not instance.hostname:
            instance.hostname=instance.image.hostname
        instance.remedy_script_todo+='\n'+utils.remedy_script_hostname(instance.hostname)
        return
    old=sender.objects.get(pk=instance.id)
    if old.hostname!=instance.hostname:
        instance.remedy(
            script=utils.remedy_script_hostname(instance.hostname),
            manual=False
        )

@receiver(pre_delete, sender=Instance)
def destroy_instance(sender,instance,**kwargs):
    #to aviold repeated deletion
    for instance in sender.objects.select_for_update().filter(pk=instance.pk):
        def destroy():
            if not instance.ready:
                print('WARNNING: delete instance under building')
            else:
                try:
                    instance.cloud.driver.vm_force_delete(
                        instance.cloud.platform_credential,
                        str(instance.uuid)
                    )
                except Exception as e:#TODO may spam the log
                    instance.pk=None
                    instance.save()
                    traceback.print_exc()
                    return
            destroyed.send(sender=sender, instance=instance, name='destroyed')
        transaction.on_commit(Thread(target=destroy).start)

@receiver(post_save, sender=Volume)
def materialize_volume(sender, instance, **kwargs):
    if not kwargs['created'] or instance.ready: return
    instance.built_time=now()
    instance.save()
    @transaction.atomic
    def materialize(volume=instance):
        volume=sender.objects.select_for_update().get(pk=volume.pk)
        remark = settings.PACKONE_LABEL+'.'+volume.cloud.name+';'
        if volume.remark: remark+=volume.remark
        info=volume.cloud.driver.volume_create(
            volume.cloud.platform_credential,
            volume.capacity,
            remark=remark
        )
        volume.uuid=UUID(info["uuid"].replace('-', ''), version=4)
        volume.built_time=info["create_time"]
        volume.status=VOLUME_STATUS.available.value
        volume.save()
        materialized.send(sender=sender, instance=volume, name='materialized')
    transaction.on_commit(Thread(target=materialize).start)

@receiver(pre_delete, sender=Volume)
def destroy_volume(sender,instance,**kwargs):
    #to aviold repeated deletion
    for volume in sender.objects.select_for_update().filter(pk=instance.pk):
        def destroy():
            if not volume.ready:
                print('WARNNING: delete volume under building')
            else:
                try:
                    volume.cloud.driver.volume_delete(
                        volume.cloud.platform_credential,
                        str(volume.uuid)
                    )
                except Exception as e:#TODO may spam the log
                    volume.pk=None
                    volume.save()
                    traceback.print_exc()
                    return
            destroyed.send(sender=sender, instance=volume, name='destroyed')
        transaction.on_commit(Thread(target=destroy).start)

@receiver(monitored, sender=Instance)
@receiver(materialized, sender=Volume)
@transaction.atomic
def mount(sender, instance, **kwargs):
    if instance.deleting: return
    instance=sender.objects.select_for_update().get(pk=instance.pk)
    if not instance.mountable: return
    mounts=instance.mount_set.select_for_update().filter(
        completed_time=None,
        volume__status = VOLUME_STATUS.available.value
    ) if sender==Instance else Mount.objects.select_for_update().filter(completed_time=None, volume=instance)
    if not mounts.exists(): return
    @transaction.atomic
    def materialize(mount):
        mount=Mount.objects.select_related('volume').select_for_update().get(pk=mount.pk)
        info=mount.volume.cloud.driver.volume_mount(
            mount.volume.cloud.platform_credential,
            str(mount.volume.uuid),
            str(mount.instance.uuid)
        )
        mount.dev=info['dev']
        mount.completed_time=info["attach_time"]
        mount.save()
        mount.instance.update_remedy_script(
            utils.remedy_script_mount_add(mount),
            heading=True
        )
        mount.volume.status=VOLUME_STATUS.mounted.value
        mount.volume.save()
        materialized.send(sender=Mount, instance=mount, name='materialized')
    for mount in mounts:
        if not mount.instance.mountable: continue
        mount.completed_time=now()
        mount.save()
        Thread(target=materialize,args=(mount,)).start()

@receiver(pre_delete, sender=Mount)
def umount(sender,instance,**kwargs):
    #to aviold repeated deletion
    for mount in sender.objects.select_for_update().filter(pk=instance.pk):
        @transaction.atomic
        def destroy(mount=mount):
            volume=Volume.objects.select_for_update().get(pk=mount.volume.pk)
            if not mount.ready:
                print('WARNNING: delete mount under building')
            else:
                try:
                    mount.volume.cloud.driver.volume_unmount(
                        mount.volume.cloud.platform_credential,
                        str(mount.volume.uuid),
                        str(mount.instance.uuid)
                    )
                except Exception as e:
                    mount.pk=None
                    mount.save()
                    traceback.print_exc()
                    return
                volume.status=VOLUME_STATUS.available.value
                volume.save()
                mount.instance.update_remedy_script(utils.remedy_script_mount_remove(mount))
            destroyed.send(sender=sender, instance=mount, name='destroyed')
        transaction.on_commit(Thread(target=destroy).start)

@receiver(materialized, sender=Instance)#TODO instance may created before be added to group
@receiver(materialized, sender=Mount)
@transaction.atomic
def materialize_group(sender,instance,**kwargs):
    if sender==Mount: instance=instance.instance
    elif instance.mount_set.all().exists(): return
    for group in instance.group_set.select_for_update():
        if group.ready: continue
        if sender==Mount and group.mounts.filter(dev=None).exists(): continue
        if sender==Instance and group.instances.filter(uuid=None).exists(): continue
        group.hosts = '###group {}###\n'.format(group.long_id)+'\n'.join([ins.hosts_record for ins in group.instances.all()])
        group.built_time=now()
        group.save()
        for ins in group.instances.all():
            ins.remedy(manual=False)
        group.remedy(utils.remedy_script_hosts_add(group.hosts),manual=False)
        materialized.send(sender=Group, instance=group, name='materialized')

@receiver(destroyed, sender=Instance)
@transaction.atomic
def destroy_group(sender,instance,**kwargs):
    for group in Group.objects.select_for_update().filter(
        deleting=True,
    ):
        if not group.instances.all().exists():
            destroyed.send(sender=Group, instance=group, name='destroyed')
            group.delete()

@receiver(monitored, sender=Instance)
@receiver(tidied, sender=GroupOperation)
@receiver(executed, sender=GroupOperation)
def monitor_group(sender, instance, **kwargs):
    if sender==Instance:
        if instance.deleting: return
        for group in instance.group_set.all():
            status=group.instances.all().aggregate(Max('status'))['status__max']#TODO use join
            Group.objects.filter(pk=group.pk).update(status=status)
            group.refresh_from_db()
            monitored.send(sender=Group, instance=group, name='monitored')
    else:
        if instance.status==OPERATION_STATUS.waiting.value: return
        instance.target.monitor()

@receiver(post_save, sender=InstanceOperation)
@receiver(post_save, sender=GroupOperation)
def tidy_operation(sender,instance,created,**kwargs):
    if not created or instance.serial: return #only following serial operations will not be tidied
    if instance.operation==INSTANCE_OPERATION.remedy.value and instance.script and not instance.tidied:
        supervisor_ops=[s.value for s in INSTANCE_OPERATION]
        ops=utils.remedy_script_tidy(instance.script,supervisor_ops)
        for i in range(len(ops)):
            op=ops[i]
            if i==0:
                if op in supervisor_ops:
                    instance.script=None
                    instance.operation=op
                    instance.tidied=True
                else:
                    instance.script=op
                    instance.tidied=True
                instance.save()
            else:
                if op in supervisor_ops:
                    op_instance=sender(
                        target=instance.target,
                        operation=op,
                    )
                else:
                    op_instance=sender(
                        target=instance.target,
                        operation=INSTANCE_OPERATION.remedy.value,
                        script=op,
                    )
                op_instance.status=OPERATION_STATUS.waiting.value
                op_instance.serial=instance
                op_instance.tidied=True
                op_instance.manual=False
                op_instance.save()
    tidied.send(sender=sender, instance=instance, name='tidied')

@receiver(monitored, sender=Instance)
@receiver(monitored, sender=Group)
@transaction.atomic#to aviod deleted target and duplicated remedy
def select_operation(sender,instance,**kwargs):
    for target in instance.__class__.objects.select_for_update().filter(pk=instance.pk):
        target.remedy(manual=False)
        ops=target.get_next_operations().select_for_update()
        if not ops.exists(): return
        for op in ops:
            if op.runnable:
                op.status=OPERATION_STATUS.running.value
                op.started_time=now()
                op.completed_time=None
                op.save()
                selected.send(sender=op.__class__, instance=op, name='selected')
                break
            else:
                op.status=OPERATION_STATUS.waiting.value
                op.save()

@receiver(selected, sender=InstanceOperation)
@receiver(selected, sender=GroupOperation)
def execute_operation(sender,instance,**kwargs):
    instance.execute()

@receiver(executed, sender=InstanceOperation)
@transaction.atomic
def close_group_operation(sender, instance, **kwargs):
    for running_op in GroupOperation.objects.select_for_update().filter(
        batch_uuid=instance.batch_uuid,
        started_time__isnull=False
    ):
        if not running_op.get_remain_oprations().exists():
            running_op.completed_time=now()
            running_op.status=running_op.get_status()
            running_op.save()
            executed.send(sender=GroupOperation, instance=running_op, name='executed')

@receiver(post_delete, sender=InstanceOperation)
def purge_group_operation(sender, instance, **kwargs):
    g_op=GroupOperation.objects.filter(batch_uuid=instance.batch_uuid).first()
    if g_op and not g_op.get_sub_operations().exists():
        g_op.delete()

@receiver(monitored, sender=Instance)
@receiver(destroyed, sender=Mount)
def cleanup(sender,instance,**kwargs):
    if sender==Instance:
        if not instance.deleting: return
        ms=instance.mount_set.all()
        if ms.exists():
            if instance.umountable:
                for m in ms:
                    m.delete()
                instance.remark+=';umounting'
                instance.save()
        else:
            instance.refresh_from_db()
            if not instance.remark.endswith('umounting'):
                instance.delete()
    else:
        if instance.instance.deleting and not instance.instance.mount_set.all().exists():
            instance.instance.delete()
        if instance.volume.deleting:
            instance.volume.delete()