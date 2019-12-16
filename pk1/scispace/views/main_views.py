# coding=utf-8

import json

from django.urls import reverse
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.http.response import JsonResponse 
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from scispace.utils import get_cluster_list, get_cluster_info, add_cluster, operate_cluster
from scispace.utils import get_cluster_instances, operate_cluster_instance, get_cluster_instance_info
from scispace.utils import get_dataset_list, get_dataset_info
from scispace.utils import get_data_instance_list, get_data_instance_info, add_data_instance, delete_data_instance
from scispace.utils import get_step_operation_list, get_step_operation_info
from scispace.utils import get_data_instance_operation_list, get_data_instance_operation_info
from scispace.utils import get_cluster_data_engine_list
from scispace.utils import get_scale_list, get_available_engines
from scispace.utils import get_data_metrics, get_hosts_metrics

LOGIN_URL = "/login/"

@login_required(login_url=LOGIN_URL)
def index(request):
	return HttpResponseRedirect(reverse("scispace_cluster_list"))


@login_required(login_url=LOGIN_URL)
def cluster_list(request):
	dic = {}
	dic["clusters"] = get_cluster_list(request.user)
	return TemplateResponse(request, "cluster_list.html", dic)


@login_required(login_url=LOGIN_URL)
def cluster_add(request):
	user_id = request.user.id
	dic = {}
	dic["scales"] = get_scale_list()
	# dic["required_engines"] = ["HDFS","HIVE","MAPREDUCE2","YARN","ZEPPELIN","HUE"]

	if request.method == "POST":
		name = request.POST.get("name")
		scale = int(request.POST.get("scale"))
		engines = request.POST.getlist("engines")
		engines = [ int(e) for e in engines]
		remedy_script_todo = request.POST.get("remedy_script_todo")
		public = request.POST.get("public")
		if public == "0":
			public = False
		else:
			public = True
		remark = request.POST.get("remark")
		add_cluster(user_id, name, scale, engines, public, remedy_script_todo, remark)	
		return HttpResponseRedirect(reverse("scispace_cluster_list"))

	scale_engines = {}  # not use ajax
	for sc in dic["scales"]:
		engines = get_available_engines(sc["id"])
		scale_engines[sc["id"]] = engines
	dic["scale_engines"] = json.dumps(scale_engines)
	return TemplateResponse(request, "cluster_add.html", dic)


@csrf_exempt
@login_required(login_url=LOGIN_URL)
def cluster_operate_ajax(request):
	"""
	cluster operations:
	("start","reboot","shutdown","poweroff","remedy")
    ("scale_in", "scale_out")
    ("destroy", )
	"""
	dic = {"res": True, "err":None}
	cluster_id = request.POST.get("cluster_id")
	op = request.POST.get("operation")
	if cluster_id.isdecimal():
		cluster_id = int(cluster_id)
		dic["res"] = operate_cluster(request.user, cluster_id, op)
	else:
		dic["res"] = False
		dic["err"] = "Invalid ID"
	return JsonResponse(dic)

@csrf_exempt
@login_required(login_url=LOGIN_URL)
def cluster_get_info_ajax(request):
	"""
	get cluster status
	"""
	dic = {"res": True, "info":None, "err":None}
	cluster_id = request.GET.get("cluster_id")	
	if cluster_id.isdecimal():
		cluster_id = int(cluster_id)
		cluster_info = get_cluster_info(request.user, cluster_id)
		if not cluster_info:
			raise Http404
		dic["info"] = {"status":cluster_info["status"], "status_name":cluster_info["status_name"]}
	else:
		dic["res"] = False
		dic["err"] = "Invalid ID"
	return JsonResponse(dic)


@login_required(login_url=LOGIN_URL)
def scale_engines_ajax(request):
	scale_id = int(request.GET.get("scale"))
	dic = {"res": True, "err":None, "list":[]}
	dic["list"] = get_available_engines(scale_id)
	return JsonResponse(dic)


@login_required(login_url=LOGIN_URL)
def cluster_info(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)	
	if not dic["cluster"]:
		raise Http404 
		
	dic["hosts"] = get_cluster_instances(request.user, c_id)
	if dic["cluster"]["portal"]:
		dic["pipeline_api_url"] = "%s/piflow-web/api/flowList" %(dic["cluster"]["portal"].replace("8080","6001").rstrip("/"))
		dic["notebook_api_url"] = "%s/api/notebook" %(dic["cluster"]["portal"].replace("8080","9995").rstrip("/"))
	else:
		dic["pipeline_api_url"] = "#"
		dic["notebook_api_url"] = "#"
	return TemplateResponse(request, "cluster_info.html", dic)

@login_required(login_url=LOGIN_URL)
def cluster_instance_list(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)	
	if not dic["cluster"]:
		raise Http404 
	dic["instances"] = get_cluster_instances(request.user, c_id)
	return TemplateResponse(request, "cluster_instance_list.html", dic)


@csrf_exempt
@login_required(login_url=LOGIN_URL)
def cluster_instance_operate_ajax(request, c_id):
	"""
	 operations:
	("toggle","delete",)
	"""
	dic = {"res": True, "err":None}
	instance_id = request.POST.get("instance_id")
	op = request.POST.get("operation")
	if instance_id.isdecimal():
		instance_id = int(instance_id)
		dic["res"] = operate_cluster_instance(request.user, c_id, instance_id, op)
	else:
		dic["res"] = False
		dic["err"] = "Invalid ID"
	return JsonResponse(dic)


@csrf_exempt
@login_required(login_url=LOGIN_URL)
def cluster_instance_get_info_ajax(request, c_id):
	"""
	get cluster instance status
	"""
	dic = {"res": True, "info":None, "err":None}
	instance_id = request.GET.get("instance_id")
	require_vnc = request.GET.get("require_vnc")
	if require_vnc == "true":
		require_vnc = True
	else:
		require_vnc = False
	if instance_id.isdecimal():
		instance_id = int(instance_id)
		instance_info = get_cluster_instance_info(request.user, instance_id,require_vnc=require_vnc)	
		if not instance_info:
			raise Http404 
		dic["info"] = {"status":instance_info["status"], "status_name":instance_info["status_name"], "vnc_url":instance_info["vnc_url"]}
	else:
		dic["res"] = False
		dic["err"] = "Invalid ID"
	return JsonResponse(dic)


@login_required(login_url=LOGIN_URL)
def dataset_list(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	dic["datasets"] = get_dataset_list(request.user)
	return TemplateResponse(request, "dataset_list.html", dic)

@login_required(login_url=LOGIN_URL)
def dataset_info(request, c_id, dt_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	dic["dataset"] = get_dataset_info(dt_id)
	return TemplateResponse(request, "dataset_info.html", dic)

@login_required(login_url=LOGIN_URL)
def dataset_load(request, c_id, dt_id):
	pass
# 	dic = {}
# 	dic["cluster"] = get_cluster_info(request.user, c_id)
# 	dic["dataset"] = get_dataset_info(dt_id)
# 	return TemplateResponse(request, "dataset_info.html", dic)

@login_required(login_url=LOGIN_URL)
def data_instance_list(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	dic["data_instances"] = get_data_instance_list(request.user, c_id)
	return TemplateResponse(request, "data_instance_list.html", dic)

@csrf_exempt
@login_required(login_url=LOGIN_URL)
def data_instance_get_info_ajax(request, c_id):
	"""
	get cluster instance status
	"""
	dic = {"res": True, "info":None, "err":None}
	instance_id = request.GET.get("instance_id")	
	if instance_id.isdecimal():
		instance_id = int(instance_id)
		instance_info = get_data_instance_info(instance_id)
		dic["info"] = {"status":instance_info["status"], "status_name":instance_info["status_name"]}
	else:
		dic["res"] = False
		dic["err"] = "Invalid ID"
	return JsonResponse(dic)

@login_required(login_url=LOGIN_URL)
def data_pipeline(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	if dic["cluster"]["portal"]:
		dic["pipeline_url"] = "%s/piflow-web/web/flowList?first" %(dic["cluster"]["portal"].replace("8080","6001").rstrip("/"))
	else:
		dic["pipeline_url"] = "#"
	return TemplateResponse(request, "data_pipeline.html", dic)

@login_required(login_url=LOGIN_URL)
def notebook(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	if dic["cluster"]["portal"]:
		dic["notebook_url"] = dic["cluster"]["portal"].replace("8080","9995")
	else:
		dic["notebook_url"] = "#"
	return TemplateResponse(request, "notebook.html", dic)

@login_required(login_url=LOGIN_URL)
def scispace_operation_list(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	dic["operations"] = get_step_operation_list(c_id)
	return TemplateResponse(request, "scispace_operation_list.html", dic)

@login_required(login_url=LOGIN_URL)
def scispace_operation_info(request, c_id, op_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	dic["operation"] = get_step_operation_info(c_id, op_id)
	return TemplateResponse(request, "scispace_operation_info.html", dic)


@login_required(login_url=LOGIN_URL)
def data_instance_operation_list(request, c_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	dic["operations"] = get_data_instance_operation_list(c_id)
	return TemplateResponse(request, "data_instance_operation_list.html", dic)



@login_required(login_url=LOGIN_URL)
def data_instance_operation_info(request, c_id, op_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	dic["operation"] = get_data_instance_operation_info(c_id,op_id)
	return TemplateResponse(request, "data_instance_operation_info.html", dic)


@login_required(login_url=LOGIN_URL)
def data_instance_add(request, c_id):
	user_id = request.user.id
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)

	if request.method == "POST":
		name = request.POST.get("name")
		dataset_id = request.POST.get("dataset_id")
		data_engine_id = request.POST.get("data_engine_id")
		remedy_script_todo = request.POST.get("remedy_script_todo")
		remark = request.POST.get("remark")
		add_data_instance(user_id, c_id, name, dataset_id, data_engine_id, remedy_script_todo, remark)

		return HttpResponseRedirect(reverse("scispace_data_instance_list", args=(c_id,)))
	
	dic["datasets"] = get_dataset_list(request.user)
	dic["dataset_id"] = request.GET.get("dataset")
	if dic["dataset_id"]:
		dic["dataset_id"] = int(dic["dataset_id"])

	data_engines = {}  # not use ajax
	for dt in dic["datasets"]:
		engines = get_cluster_data_engine_list(c_id, dt["id"])
		data_engines[dt["id"]] = [{"id":e["id"],"name":e["engine_name"]} for e in engines]
	dic["data_engines"] = json.dumps(data_engines)

	return TemplateResponse(request, "data_instance_add.html", dic)


@login_required(login_url=LOGIN_URL)
def data_instance_delete(request, c_id):
	user_id = request.user.id
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)

	if request.method == "POST":
		data_instance_id = request.POST.get("data_instance_id")
		data_instance = get_data_instance_info(data_instance_id)
		if not data_instance or data_instance["owner"].id != request.user.id:
			raise Http404
		delete_data_instance(request.user, data_instance_id)
		return HttpResponseRedirect(reverse("scispace_data_instance_list", args=(c_id,)))
	
	data_instance_id = request.GET.get("dt_id")
	if data_instance_id:
		data_instance_id = int(data_instance_id)

	data_instance = get_data_instance_info(data_instance_id)
	if not data_instance or data_instance["owner"].id != request.user.id:
		raise Http404

	dic["data_instance"] = data_instance
	return TemplateResponse(request, "data_instance_delete.html", dic)



@login_required(login_url=LOGIN_URL)
def data_instance_query(request, c_id, di_id):
	dic = {}
	dic["cluster"] = get_cluster_info(request.user, c_id)
	data_instance = get_data_instance_info(di_id)
	dic["query_url"] = data_instance["query_url"]
	dic["data_instance"] = data_instance
	return TemplateResponse(request, "data_instance_query.html", dic)



@login_required(login_url=LOGIN_URL)
def get_data_engines_ajax(request, c_id):
	dic = {"res": True, "err":None, "list":[]}
	dataset_id = request.GET.get("dataset_id")
	dataset_id = int(dataset_id)
	engines = get_cluster_data_engine_list(c_id, dataset_id)
	dic["list"] = [{"id":e["id"],"name":e["engine_name"]} for e in engines]
	return JsonResponse(dic)


@login_required(login_url=LOGIN_URL)
def get_data_metrics_ajax(request, c_id):
	dic = {"res": True, "err":None, "metrics":[]}
	metrics = get_data_metrics(c_id)
	dic["metrics"] = metrics
	return JsonResponse(dic)


@login_required(login_url=LOGIN_URL)
def get_hosts_metrics_ajax(request, c_id):
	dic = {"res": True, "err":None, "metrics":[]}
	metrics = {}
	dic["metrics"] = get_hosts_metrics(request.user, c_id)
	return JsonResponse(dic)

