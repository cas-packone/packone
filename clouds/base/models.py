from uuid import uuid4
from enum import Enum
from threading import Thread
from django.db import models
from django.db import transaction
from django.dispatch import Signal
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from django.utils.timezone import now

class StaticModel(models.Model):
    name=models.CharField(max_length=50,unique=True)
    _remedy_script=models.TextField(max_length=5120,default="",blank=True)
    public=models.BooleanField(default=False)
    enabled=models.BooleanField(default=True)
    modified_time=models.DateTimeField(auto_now=True)
    created_time=models.DateTimeField(auto_now_add=True)
    remark = models.CharField(blank=True,null=True,max_length=100)
    owner=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    class Meta:
        abstract = True
    def __str__(self):
        return "{}".format(self.name)
    @cached_property
    def remedy_script(self):
        return "###remedy {}: {}###\n{}\n".format(
            self._meta.verbose_name,
            self.name,
            self._remedy_script
        ) if self._remedy_script else ""

#TODO class VLan

class INSTANCE_STATUS(Enum):#greater value means worse status
    null=0 #unknown
    active=1
    block=2
    suspend=3
    shutdown=4
    poweroff=5
    breakdown=6
    pause=7
    failure=8 #libvirt reserv code
    host_lost=9
    instance_lost=10
    building=11

class OperatableMixin(object):
    @property
    def startable(self):
        if self.status in [
            INSTANCE_STATUS.poweroff.value,
            INSTANCE_STATUS.shutdown.value,
        ]: return True
        return False
    @property
    def stopable(self):
        return self.status == INSTANCE_STATUS.active.value
    def monitor(self,notify=True):
        if not self.ready: raise Exception('instance not ready')
        status = self.cloud.driver.vm_status(self.cloud.platform_credential,str(self.uuid))
        if self.__class__.objects.filter(pk=self.pk).update(status=status):
            self.refresh_from_db()
            if notify: monitored.send(sender=self.__class__, instance=self, name='monitored')
    def update_remedy_script(self,script,heading=False):
        if heading:
            v=models.Value(script+'\n')
            c=models.functions.Concat(v,'remedy_script_todo')
        else:
            v=models.Value('\n'+script)
            c=models.functions.Concat('remedy_script_todo',v)
        self.__class__.objects.filter(pk=self.pk).update(remedy_script_todo=c)
    def get_ready_operations(self):
        return self.get_operation_model().objects.filter(
            started_time__isnull=True,
            completed_time__isnull=True,
            status=OPERATION_STATUS.running.value,
            target=self
        ).exclude(target__deleting=True, manual=False).order_by("id")
    def get_running_operations(self):
        return self.get_operation_model().objects.filter(
            started_time__isnull=False,
            completed_time__isnull=True,
            target=self
        ).order_by("started_time")
    def get_next_operations(self):
        return self.get_operation_model().objects.filter(
            target=self,
            status=OPERATION_STATUS.waiting.value
        ).exclude(target__deleting=True, manual=False).order_by("id")
    def get_former_operation(self):
        return self.get_operation_model().objects.filter(
            target=self,
            status__in=[
                OPERATION_STATUS.success.value,
                OPERATION_STATUS.failed.value
            ]
        ).order_by("-started_time").first()
        
monitored = Signal(providing_args=["instance","name"])

class VOLUME_STATUS(Enum):#greater value means worse status
    null=0 #unknown
    available=1
    mounted=2
    building=3 #executing remedy_script

class INSTANCE_OPERATION(Enum):
    start="start"
    reboot="reboot"
    shutdown="shutdown"
    poweroff="poweroff"
    remedy="remedy"

class OPERATION_STATUS(Enum):
    success="success"
    failed="failed"
    running="running"
    waiting="waiting"

#TODO allow restart faild operation
class OperationModel(models.Model):
    operation=models.CharField(max_length=50,choices=[(op.value,op.name) for op in INSTANCE_OPERATION],default=INSTANCE_OPERATION.start.value)
    batch_uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    script=models.TextField(max_length=5120,blank=True,null=True)
    serial=models.ForeignKey("self",on_delete=models.CASCADE,blank=True,null=True,editable=False)
    created_time=models.DateTimeField(auto_now_add=True)
    started_time=models.DateTimeField(blank=True,null=True,editable=False)
    completed_time=models.DateTimeField(blank=True,null=True,editable=False)
    status=models.CharField(max_length=50,choices=[(s.value,s.name) for s in OPERATION_STATUS],default=OPERATION_STATUS.running.value,editable=False)
    tidied = models.BooleanField(default=False,editable=False)
    manual = models.BooleanField(default=True,editable=False)
    class Meta:
        verbose_name = "operation"
        abstract = True
    def __str__(self):
        return "{}/{}/{}/{}".format(self.target,self.operation,self.pk,self.status)
    @cached_property
    def is_boot(self):
        return self.operation in (INSTANCE_OPERATION.start.value,INSTANCE_OPERATION.reboot.value)
    @property
    def executing(self):
        return self.started_time and not self.completed_time
    @property
    def runnable(self):
        if self.executing: return False
        if self.manual:
            if self.status!=OPERATION_STATUS.running.value: return False
            return True
        target=self.target
        if not target.stopable and self.operation==INSTANCE_OPERATION.remedy.value: return False
        if target.get_running_operations().exists(): return False
        former=target.get_former_operation()
        if former and former.status==OPERATION_STATUS.failed.value: return False
        return True
    def execute(self):
        self.__class__.objects.filter(pk=self.pk).update(
            status=OPERATION_STATUS.running.value,
            started_time=now(),
            completed_time=None
        )

class M2MOperatableMixin(OperatableMixin):
    def monitor(self):
        for operatable in self.operatables:
            Thread(target=operatable.monitor).start()

executed = Signal(providing_args=["instance","name"])

class M2MOperationModel(OperationModel):
    class Meta:
        verbose_name = "operation"
        abstract = True
    def get_status(self):
        if self.get_sub_operation_model().objects.filter(
            batch_uuid=self.batch_uuid,
            status=OPERATION_STATUS.waiting.value
        ).exists(): return OPERATION_STATUS.waiting.value
        if self.get_sub_operation_model().objects.filter(
            batch_uuid=self.batch_uuid,
            status=OPERATION_STATUS.running.value
        ).exists(): return OPERATION_STATUS.running.value
        if self.get_sub_operation_model().objects.filter(
            batch_uuid=self.batch_uuid,
            status=OPERATION_STATUS.failed.value
        ).exists(): return OPERATION_STATUS.failed.value
        return OPERATION_STATUS.success.value
    def get_remain_oprations(self):
        return self.get_sub_operation_model().objects.filter(
            batch_uuid=self.batch_uuid,
            completed_time=None
        ).order_by('started_time')
    @transaction.atomic
    def execute(self):
        super().execute()
        self=self.__class__.objects.select_for_update().get(pk=self.pk)
        operatables=self.target.operatables
        if not operatables.exists():
            self.status=OPERATION_STATUS.running.value
            self.completed_time=now()
            self.save()
            from clouds.models import executed
            executed.send(sender=self.__class__, instance=self, name='executed')
            return
        for operatable in operatables:
            self.get_sub_operation_model()(
                operation=self.operation,
                batch_uuid=self.batch_uuid,
                target=operatable,
                tidied=True,
                manual=self.manual,
                script=self.script
            ).save()