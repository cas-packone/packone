from uuid import uuid4
from enum import Enum
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from engines.models import Engine, COMPONENT_STATUS, COMPONENT_OPERATION
from clouds.base.models import StaticModel, OperationModel, OperatableMixin
from clouds.models import OPERATION_STATUS, INSTANCE_STATUS
from engines.models import Cluster#TODO use worldwide namespace when upload to pip

class DataSource(StaticModel):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    uri=models.CharField(max_length=200,help_text='specify the protocol and address used to sync this remote data source.')
    sync_interval=models.PositiveIntegerField(default=3600, validators=[MinValueValidator(1)],verbose_name="sync interval in seconds")
    description=models.TextField(max_length=5120)
    
class DATASET_TYPE(Enum):
    ralational=0
    raw=1 #无结构
    freetext=2
    semistructed=3
    event=4
    graph=5

#TODO security exposure risk: data load histoy cmd in the relying cluster
class Dataset(StaticModel):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    source=models.ForeignKey(DataSource,on_delete=models.PROTECT,blank=True,null=True)
    uri=models.CharField(max_length=2000)
    type=models.PositiveIntegerField(blank=True,null=True,choices=[(type.value,type.name) for type in DATASET_TYPE])
    size=models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    description=models.TextField(max_length=5120)
    @property
    def type_name(self):
        return DATASET_TYPE(self.type).name

class DataEngine(StaticModel):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    type=models.PositiveIntegerField(choices=[(type.value,type.name) for type in DATASET_TYPE])
    engine=models.ForeignKey(Engine,on_delete=models.PROTECT)
    uri_prefix=models.CharField(max_length=2000, default='', blank=True)
    description=models.TextField(max_length=5120)
    
class DataInstance(models.Model,OperatableMixin):
    uuid=models.UUIDField(auto_created=True, default=uuid4, editable=False)
    name=models.CharField(max_length=50)
    dataset=models.ForeignKey(Dataset,on_delete=models.PROTECT)
    cluster=models.ForeignKey(Cluster,on_delete=models.PROTECT)
    engine=models.ForeignKey(DataEngine,on_delete=models.PROTECT)#TODO:its uri should be the prefix of the final uri
    remedy_script_todo=models.TextField(max_length=51200,default="",blank=True)
    created_time=models.DateTimeField(auto_now_add=True)
    built_time=models.DateTimeField(blank=True,null=True,editable=False)
    owner=models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    status= models.PositiveIntegerField(choices=[(status.value,status.name) for status in COMPONENT_STATUS],default=COMPONENT_STATUS.null.value,editable=False)
    remark = models.CharField(blank=True,null=True,max_length=100)
    deleting = models.BooleanField(default=False,editable=False)
    class Meta:
        unique_together = (('name','cluster','owner'),('engine','name',))
    def __str__(self):
        return "{}".format(self.name)
    @cached_property
    def entry_host(self):#the host to execute load dataset operations
        if self.engine.name=='EventDB': return self.cluster.find_instance('master1.packone')
        return self.engine.engine.get_host(self.cluster)
    @cached_property
    def uri_suffix(self):#suffix of the final uri, the only approach to access this data instance.
        return self.name.replace(' ','-')
    @cached_property
    def uri(self):#suffix of the final uri, the only approach to access this data instance.
        return self.engine.uri_prefix.format(instance=self.entry_host)+self.uri_suffix
    @property
    def startable(self):
        if self.status == COMPONENT_STATUS.null.value: return True#TODO stop
        return False
    @staticmethod
    def get_operation_model():
        return DataInstanceOperation
    @property
    def ready(self):
        return self.built_time
    @property
    def building(self):
        return self.built_time and not self.ready
    @property
    def host(self):
        return self.built_time and not self.ready
    # @property
    # def uri_total(self):#TODO opt. perf.
    #     endpoints=[]
    #     for ins in self.cluster.instances.filter(image__in=self.engine.component.images.all()):
    #         endpoints.append(ins.hostname+"://"+self.engine.endpoint)
    #     return [endpoint+"://"+self.uri_suffix for endpoint in endpoints]
    # @property
    # def uri_alive(self):
    #     endpoints=[]
    #     for ins in self.space.pilot.cluster.instance_set.filter(image__in=self.engine.component.images.all(),status=clouds.models.INSTANCE_STATUS.running.value):
    #         endpoints.append(ins.hostname+"://"+self.engine.endpoint)
    #     return [endpoint+"://"+self.uri_suffix for endpoint in endpoints]
    # @property
    # def uri_elected(self):
    #     if not self.uri_alive:
    #         return None
    #     return self.uri_alive[0]#TODO make load banlance
    # @property
    # def status_name(self):
    #     return COMPONENT_STATUS(self.status).name
    # def update_status(self):
    #     pes=self.engine.component.engine_set.filter(id__in=self.space.pilot.engines.all())
    #     self.status=pes[0].status(self.space.pilot)
    #     self.save()

class DataInstanceOperation(OperationModel):
    #TODO add custom validator for operation 'start' on 'running' instance. model.clean()?
    #TODO add custom validator for allowed operation.
    operation=models.CharField(max_length=50,choices=[(op.value,op.name) for op in COMPONENT_OPERATION],default=COMPONENT_OPERATION.start.value)
    target=models.ForeignKey(DataInstance,on_delete=models.CASCADE)
    log=models.TextField(max_length=51200,null=True,editable=False)
    def execute(self):
        self.completed_time=datetime.datetime.now()
        self.save()
        #TODO add data instance monitoring
        # print('{}:{}'.format(instance.target.ipv4,result))