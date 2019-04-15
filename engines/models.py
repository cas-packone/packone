import time
from uuid import uuid4
from enum import Enum
from threading import Thread
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from clouds.models import StaticModel, Image, Instance, Mount, INSTANCE_STATUS, INSTANCE_OPERATION, OPERATION_STATUS, InstanceBlueprint, InstanceOperation, OperatableMixin, OperationModel, Group, GroupOperation
from django.utils.functional import cached_property
from django.db import transaction
from clouds.base.models import M2MOperatableMixin, M2MOperationModel

class COMPONENT_STATUS(Enum):
    null=0 #unknown
    active=1
    block=2
    suspend=3
    stop=4
    breakdown=5
    pause=6
    instance_lost=7

class COMPONENT_TYPE(Enum):
    master="master"
    slave="slave"
    client="client"

class COMPONENT_OPERATION(Enum):
    start="start"
    stop="stop"
    # restart="restart"

class Component(StaticModel):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    images=models.ManyToManyField(Image)
    type=models.CharField(max_length=50,choices=[(type.value,type.name) for type in COMPONENT_TYPE])
    endpoint=models.CharField(max_length=200)

class Engine(StaticModel):#TODO make Engine customizable in the ui
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    components=models.ManyToManyField(Component)
    def start(self, pilot):
        print(utils.ambari_service_start('admin','admin',pilot.portal,self.name.upper()))
    def stop(self, pilot):
        print(utils.ambari_service_stop('admin','admin',pilot.portal,self.name.upper()))
    def status(self, pilot):
        state=utils.ambari_service_status('admin','admin',pilot.portal,self.name.upper())['ServiceInfo']['state']
        if state=='INSTALLED':
            return COMPONENT_STATUS.stop.value
        elif state=='STARTED':
            return COMPONENT_STATUS.running.value
        else:
            return COMPONENT_STATUS.null.value

class Scale(StaticModel):
    init_blueprints=models.ManyToManyField(InstanceBlueprint,related_name="initialized_scales")
    step_blueprints=models.ManyToManyField(InstanceBlueprint,related_name="stepped_scales",blank=True)
    auto=models.BooleanField(default=False)
    def __str__(self):
        return "{}/{}".format(
            self.name,
            'auto' if self.auto else 'manual',
        )
    @cached_property
    def init_size(self):
        q=0
        for ib in self.init_blueprints.all():
            q+=ib.quantity
        return q
    @cached_property
    def step_size(self):
        q=0
        for ib in self.step_blueprints.all():
            q+=ib.quantity
        return q
    def scale(self, owner, current_step=0, remark=None):
        step=Group(owner=owner)
        step.save()
        if not current_step:#init
            if not remark: remark='initialized from scale: {}'.format(self.name)
            step.remark=remark
            for ib in self.init_blueprints.all():
                inss=ib.launch(owner=owner, remark=remark)
                step.instances.add(*inss)
        else:
            if not remark: remark='scaled from scale: {}'.format(self.name)
            step.remark=remark
            for ib in self.step_blueprints.all():
                next_number=ib.quantity*(current_step-1)+1
                if self.init_blueprints.filter(pk=ib.pk).exists():
                    next_number+=ib.quantity
                inss=ib.launch(owner=owner, next_number=next_number, remark=remark)
                step.instances.add(*inss)
        step.remark=remark
        step.save()
        return step

class Cluster(models.Model,M2MOperatableMixin):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    name=models.CharField(max_length=50)
    scale=models.ForeignKey(Scale,on_delete=models.PROTECT)
    engines=models.ManyToManyField(Engine,blank=True)
    steps=models.ManyToManyField(Group,blank=True,editable=False)
    public=models.BooleanField(default=False)
    remedy_script_todo=models.TextField(max_length=51200,default="",blank=True)
    remark = models.CharField(blank=True,null=True,max_length=100)
    owner=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    created_time=models.DateTimeField(auto_now_add=True)
    built_time=models.DateTimeField(blank=True, null=True, editable=False)
    status= models.PositiveIntegerField(choices=[(status.value,status.name) for status in INSTANCE_STATUS],default=INSTANCE_STATUS.building.value,editable=False)
    deleting = models.BooleanField(default=False,editable=False)
    class Meta:
        unique_together = ('name', 'owner')
    def __str__(self):
        return "{}".format(self.name)
    @staticmethod
    def get_operation_model():
        return ClusterOperation
    @property
    def operatables(self):
        return self.steps.all()
    @property
    def ready(self):
        return self.built_time
    @property
    def building(self):
        return self.built_time and not self.ready
    def get_ready_steps(self):
        return self.steps.filter(built_time__isnull=False)
    def get_instances(self):
        return Instance.objects.filter(group__in=self.steps.filter()).distinct()
    def get_ready_instances(self):
        return Instance.objects.filter(group__in=self.get_ready_steps()).distinct()
    @cached_property
    def portal(self):#TODO formalize, opt perf.
        if not self.ready: raise Exception('cluster not ready')
        mi=self.get_ready_instances().filter(image__name__contains='master1')
        if mi.exists(): return "http://"+str(mi[0].ipv4)+':8080'
        return None
    @cached_property
    def engines_unselected(self):
        return Engine.objects.all().difference(self.engines.all())
    @transaction.atomic
    def scale_one_step(self):# the only way to scale cluster
        cluster=self.__class__.objects.select_for_update().get(pk=self.pk)
        step=cluster.scale.scale(
            owner=cluster.owner,
            current_step=cluster.steps.count(),
            remark='cluster: '+cluster.name
        )
        cluster.steps.add(step)
    def delete(self, *args, **kwargs):
        if not self.ready:
            print('WARNNING: delete {} under building'.format(self._meta.verbose_name))
        operatables=self.operatables
        if operatables.exists():
            self.deleting=True
            self.save()
            for operatable in operatables:
                operatable.delete()
        else:
            super().delete(*args, **kwargs)
    # def start(self):
    #     return utils.ambari_service_start_all('admin','admin',self.portal)#TODO use credential args
    # def stop(self):
    #     return utils.ambari_service_stop_all('admin','admin',self.portal)
    # def add_selected_engines(self):
    #     for e in self.engines.all():
    #         #set maintaince mode instead of removing
    #         utils.ambari_service_maintenance_off('admin','admin',self.portal,e.name.upper())
    # def remove_unselected_engines(self):
    #     for e in self.engines_unselected:
    #         #set maintaince mode instead of removing
    #         utils.ambari_service_maintenance_on('admin','admin',self.portal,e.name.upper())
    # @cached_property
    # def init_size(self):
    #     size=0
    #     for ib in self.blueprint.instance_blueprints.all():
    #         size+=ib.quantity
    #     return size
    def find_instance(self,hostname):
        matched_ins=self.instances.filter(hostname=hostname)
        return matched_ins[0] if matched_ins.exists() else None

class ClusterOperation(M2MOperationModel):
    target=models.ForeignKey(Cluster,on_delete=models.CASCADE)
    @staticmethod
    def get_sub_operation_model():
        return GroupOperation