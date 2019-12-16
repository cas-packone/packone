# coding=utf-8

from django.contrib.auth.models import User
from django.db.models import Q

from engines.models import Cluster, StepOperation, Scale
from engines.models import COMPONENT_OPERATION
from data.models import Dataset, DataInstance, DataInstanceOperation, DataEngine
from data.models import INSTANCE_STATUS as DATA_INSTANCE_STATUS
from clouds.models import OPERATION_STATUS, INSTANCE_STATUS, INSTANCE_OPERATION
from clouds.models import Instance, InstanceOperation

def _cluster_info(obj):
    return {
        'id': obj.id,
        'uuid' : obj.uuid,
        'name' : obj.name,
        'scale' : obj.scale,
        'engines' : obj.engines,
        'steps' : obj.steps,
        'remedy_script_todo' : obj.remedy_script_todo,
        'remark' : obj.remark,
        'public' : obj.public,
        'owner' : obj.owner,
        'created_time' : obj.created_time,
        'built_time' : obj.built_time,
        'status' : obj.status,
        'status_name': INSTANCE_STATUS(obj.status).name,        
        'deleting' : obj.deleting,
        'portal' : obj.portal if obj.ready else None,
    }

def get_cluster_list(req_user: User) -> list:
    objs = Cluster.objects.filter(deleting=False).order_by("-id")   
    if not req_user.is_superuser:
        objs = objs.filter(Q(owner=req_user) | Q(public=True))
    return [_cluster_info(obj) for obj in objs]

def _get_cluster_obj(req_user: User, c_id) -> Cluster:
    objs = Cluster.objects.filter(id=c_id, deleting=False)
    if not req_user.is_superuser:
        objs = objs.filter(Q(owner=req_user) | Q(public=True)) 
    if objs.exists():
        return objs.first()
    return None

def get_cluster_info(req_user: User, c_id) -> dict:
    obj = _get_cluster_obj(req_user, c_id)
    if obj != None:
        return _cluster_info(obj)
    return None

def operate_cluster(req_user: User, c_id: int, operation: str) -> bool:
    ops1 = ("start","reboot","shutdown","poweroff","remedy")
    ops2 = ("scale_in", "scale_out")
    ops3 = ("destroy", )
    if (operation not in ops1) and (operation not in ops2) and (operation not in ops3):
        return False

    objs = Cluster.objects.filter(id=c_id, deleting=False)
    if not req_user.is_superuser:
        objs = objs.filter(Q(owner=req_user) | Q(public=True)) 
    if objs.exists():
        obj = objs.first()
        if operation in ops1:
            op = INSTANCE_OPERATION(operation)
            obj.get_operation_model()(
                    target=obj,
                    operation=op.value,
                    status=OPERATION_STATUS.running.value
                ).save()
        elif operation == "scale_out" :  
            obj.scale_one_step()
        elif operation == "scale_in" : 
            obj.steps.last().delete()
        elif operation == "destroy" :
            obj.delete()
        return True

    return False


def add_cluster(owner_id, name, scale, engines, public=False, remedy_script_todo=None, remark=None):
    obj = Cluster()
    obj.owner_id = owner_id
    obj.name = name
    obj.scale_id = scale
    obj.public = public
    obj.remedy_script_todo = remedy_script_todo
    obj.remark = remark
    obj.save()
    obj.engines.set(engines)


def _get_cluster_instance_info(obj, require_vnc=False):
    vnc_url = None
    try:
        if require_vnc:
            vnc_url = obj.vnc_url
    except Exception as e:
        pass

    return {
            "id": obj.id,
            "ipv4": obj.ipv4,
            "ipv6": obj.ipv6,
            "cloud_id": obj.cloud_id,
            "cloud_name": obj.cloud.name,
            "uuid": obj.uuid,
            "image_id": obj.image.id,
            "image_name": obj.image.name,
            "template_id": obj.template.id,
            "template_name": obj.template.name,
            "hostname": obj.hostname,
            "remedy_script_todo": obj.remedy_script_todo,
            "created_time": obj.created_time,
            "built_time": obj.built_time,
            "remark": obj.remark,
            "owner": obj.owner,
            "status": obj.status,
            "status_name": INSTANCE_STATUS(obj.status).name,            
            "deleting": obj.deleting,
            "vnc_url": vnc_url,
            
    }

def get_cluster_instances(req_user: User, c_id, require_vnc=False) -> list:
    obj = _get_cluster_obj(req_user, c_id)
    if obj != None:
        return [_get_cluster_instance_info(instance, require_vnc=require_vnc) for instance in obj.get_instances()   ]     
    return []

def get_cluster_instance_info(req_user:User, instance_id, require_vnc=False) -> dict:
    objs = Instance.objects.filter(id=instance_id)
    if objs.exists():
        return _get_cluster_instance_info(objs.first(), require_vnc=require_vnc)
    return None


def operate_cluster_instance(req_user: User, c_id: int, instance_id: int, operation: str) -> bool:
    ops1 = ("toggle","delete")
    if operation not in ops1 :
        return False

    objs = Instance.objects.filter(id=instance_id)
    if not req_user.is_superuser:
        objs = objs.filter(owner=req_user) 
    if objs.exists():
        obj = objs.first()
        if operation in ops1:
            InstanceOperation(
                target=obj,
                operation=INSTANCE_OPERATION.poweroff.value if obj.status==INSTANCE_STATUS.active.value else INSTANCE_OPERATION.start.value
            ).save()       
        elif operation == "delete" :  
            obj.delete()
        return True
    return False



def _scale_info(obj):
    return {
        "id": obj.id,
        "name": obj.name,
        # "engines": [{"id": e.id, "name":e.name} for e in obj.available_engines]
    }


def get_scale_list():
    objs = Scale.objects.filter(enabled=True)
    return [_scale_info(obj) for obj in objs]
    

def get_available_engines(scale_id):
    scales = Scale.objects.filter(id=scale_id)
    required = ["HDFS","HIVE","MAPREDUCE2","YARN","TEZ","HBASE","PIG",
                "ZOOKEEPER","AMBARI_METRICS","SPARK","SPARK2","AMBARI_INFRA",
                "ASTROSERV","GSTORE","EVENTDB","PIFLOW","SIMBA","REDIS","SLIDER","SPARKJS",
                "ZEPPELIN","HUE"]
    if scales.exists():
        obj = scales.first()
        res = []
        if obj.stack:
            for e in obj.available_engines:
                if e.name in required:
                    res.append({"id": e.id, "name":e.name, "required":True})
                else:
                    res.append({"id": e.id, "name":e.name, "required":False})
        return res
    return []


def _dataset_info(obj):
    return {
            'id': obj.id,
            'name': obj.name,
            'uuid': obj.uuid,
            'source': obj.source,
            'uri': obj.uri,
            'type': obj.type,
            'type_name': obj.type_name,
            'size': obj.size,
            'description': obj.description,
            'public': obj.public,
            'enabled': obj.enabled,
            'modified_time': obj.modified_time,
            'created_time': obj.created_time,
            'remark': obj.remark,
            'owner': obj.owner,
        }


def get_dataset_list(req_user: User) -> list:
    objs = Dataset.objects.filter(enabled=True).order_by("-id") 
    if not req_user.is_superuser:
        objs = objs.filter(Q(owner=req_user) | Q(public=True))
    return [_dataset_info(obj) for obj in objs]


def get_dataset_info(dt_id):
    objs = Dataset.objects.filter(id=dt_id, enabled=True)
    if objs.exists():
        return _dataset_info(objs.first())
    return None


def _engine_info(obj):
    return {
        'id': obj.id,
        'uuid': obj.uuid,
        'name': obj.name,
        'description': obj.description,
    }


def _data_instance_info(obj):
    query_url = ""
    if obj.cluster.ready:
        query_url = obj.cluster.portal.replace("8080","8888").rstrip("/")
        if obj.engine:
            engine_name = obj.engine.name.strip().lower()
            if engine_name == "hive":
                query_url += "/beeswax/#query"
            elif engine_name == "hdfs":
                query_url += "/filebrowser/#" + obj.uri
            elif engine_name == "hbase":
                query_url += "/hbase/"
            elif obj.uri.strip():
                query_url = obj.uri.strip()
                if query_url.startswith("http"):
                    if query_url.count("+") > 0:
                        query_url = query_url.split("+")[0].strip()
                else:
                    query_url = ""
    return {
        'id': obj.id,
        'uuid': obj.uuid,
        'name': obj.name,
        'remedy_script_todo': obj.remedy_script_todo,
        'created_time': obj.created_time,
        'built_time': obj.built_time,
        'owner': obj.owner,
        'status': obj.status,
        'status_name': DATA_INSTANCE_STATUS(obj.status).name,
        'remark': obj.remark,
        'deleting': obj.deleting,
        'dataset': _dataset_info(obj.dataset),      
        'cluster': _cluster_info(obj.cluster),
        'engine': _engine_info(obj.engine),
        'engine_lower_name':obj.engine.name.strip().lower() if obj.engine else None,
        'uri': obj.uri,
        'query_url': query_url,
    }



def get_data_instance_list(req_user: User, cluster_id) -> list:
    objs = DataInstance.objects.filter(cluster_id = cluster_id).order_by("-id") 
    if not req_user.is_superuser:
        objs = objs.filter(owner=req_user)
    return [_data_instance_info(obj) for obj in objs]

def get_data_instance_info(di_id):
    objs = DataInstance.objects.filter(id=di_id)
    if objs.exists():
        return _data_instance_info(objs.first())
    return None

def add_data_instance(owner_id, cluster_id, name, dataset_id, data_engine_id, remedy_script_todo=None, remark=None):
    obj = DataInstance()
    obj.owner_id = owner_id
    obj.name = name
    obj.dataset_id = dataset_id
    obj.cluster_id = cluster_id
    obj.engine_id = data_engine_id
    obj.remedy_script_todo = remedy_script_todo
    obj.remark = remark
    obj.save()

def delete_data_instance(req_user: User, di_id):
    objs = DataInstance.objects.filter(id=di_id, deleting=False)
    if not req_user.is_superuser:
        objs = objs.filter(owner=req_user)
    objs.delete()

# scispace operations
def _step_operation_info(obj):
    return {
    'id': obj.id,
    'name': str(obj),
    'operation': obj.operation,
    'operation_name': INSTANCE_OPERATION(obj.operation).name,
    'batch_uuid': obj.batch_uuid,
    'script': obj.script,
    'log': obj.log,
    'serial': obj.serial,
    'created_time': obj.created_time,
    'started_time': obj.started_time,
    'completed_time': obj.completed_time,
    'status': obj.status,
    'tidied': obj.tidied,
    'manual': obj.manual,
    'cluster': obj.target,
    }


def get_step_operation_list(cluster_id):
    cluster_obj = Cluster.objects.filter(id=cluster_id, deleting=False).first()
    objs = StepOperation.objects.filter(target__cluster = cluster_obj).exclude(status=OPERATION_STATUS.success.value)
    return [_step_operation_info(obj) for obj in objs]

def get_step_operation_info(cluster_id, op_id):
    cluster_obj = Cluster.objects.filter(id=cluster_id, deleting=False).first()
    objs = StepOperation.objects.filter(target__cluster = cluster_obj, id=op_id)
    if objs.exists():
        return _step_operation_info(objs.first())
    return None


# data instance operations
def _cloud_instance_operation_info(obj):
    return {
    'id': obj.id,
    'name': str(obj),
    'operation': obj.operation,
    'operation_name': INSTANCE_OPERATION(obj.operation).name,
    'batch_uuid': obj.batch_uuid,
    'script': obj.script,
    'serial': obj.serial,
    'created_time': obj.created_time,
    'started_time': obj.started_time,
    'completed_time': obj.completed_time,
    'status': obj.status,
    'tidied': obj.tidied,
    'manual': obj.manual,   
    'target': obj.target,
    'log': obj.log,
    }


def get_data_instance_operation_list(cluster_id):
    objs = InstanceOperation.objects.filter(script__contains=("mkdir -p /data/packone/"))
    return [_cloud_instance_operation_info(obj) for obj in objs]

def get_data_instance_operation_info(cluster_id,op_id):
    objs = InstanceOperation.objects.filter(id=op_id)
    if objs.exists():
        return _cloud_instance_operation_info(objs.first())
    return None

def _data_engine_info(obj):
    return {
        "id": obj.id,
        "engine": obj.engine,
        "engine_name": obj.engine.name,
        "uuid": obj.uuid,
        "uri_prefix": obj.uri_prefix,
        "description": obj.description
    }

def get_cluster_data_engine_list(cluster_id, dataset_id):    
    if not cluster_id or not dataset_id:
        return []
    qs = DataEngine.objects.filter(
            engine__in = Cluster.objects.get(pk=cluster_id).engines.all(),
            type=Dataset.objects.get(pk=dataset_id).type
        ).order_by('-pk')
    return [_data_engine_info(obj) for obj in qs]
        


from datetime import timedelta, datetime
from django.db.models import Sum, Count
import data.models as models
def get_data_metrics(cluster_id):
    today = datetime.now()
    begin_day = today - timedelta(days=365)
    state = {
        # 'cluster':{},
        'dataset':{},
        'instance':{},
        # 'space':{}
    }
    space = Cluster.objects.filter(id=cluster_id).first()
    state['dataset']['type_cnt']=[{'type': models.DATASET_TYPE(pair['type']).name, 'cnt': pair['cnt']} for pair in list(models.Dataset.objects.values('type').annotate(cnt=Count('id')))]
    state['dataset']['type_size']=[{'type': models.DATASET_TYPE(pair['type']).name, 'size': pair['size']} for pair in list(models.Dataset.objects.all().values('type').annotate(size=Sum('size')))]
    state['dataset']['public_size']=list(models.Dataset.objects.values('public').annotate(size=Sum('size')))
    state['dataset']['owner_size']=list(models.Dataset.objects.values('owner__username').annotate(size=Sum('size')).order_by('-size')[0:10])
    state['dataset']['month_size']=list(models.Dataset.objects.filter(modified_time__range=(begin_day, today)).values('modified_time__year', 'modified_time__month').annotate(size=Sum('size')).order_by('modified_time__year', 'modified_time__month'))
    state['instance']['status_cnt']=[{'status': models.INSTANCE_STATUS(pair['status']).name, 'cnt': pair['cnt']} for pair in list(models.DataInstance.objects.filter(cluster=space).values('status').annotate(cnt=Count('id')))]
    state['instance']['type_cnt']=[{'dataset__type': models.DATASET_TYPE(pair['dataset__type']).name, 'cnt': pair['cnt']} for pair in list(models.DataInstance.objects.filter(cluster=space).values('dataset__type').annotate(cnt=Count('id')).order_by('-cnt')[0:10])]
    state['instance']['dataset_cnt']=list(models.DataInstance.objects.filter(cluster=space).values('dataset__name').annotate(cnt=Count('id')).order_by('-cnt')[0:10])
    
    return state

def get_hosts_metrics(req_user: User, c_id) -> dict:
    obj = _get_cluster_obj(req_user, c_id)
    metrics = obj.metrics
    return metrics
