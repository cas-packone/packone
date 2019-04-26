from . import models
from . import serializers
from rest_framework import viewsets
from django_filters import rest_framework as filters
from django.db.models import Q
from clouds import permissions
import clouds
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from rest_framework.permissions import SAFE_METHODS
from rest_framework.decorators import api_view
from django.db.models import Sum, Count
from rest_framework.response import Response
from datetime import timedelta, datetime
from dal import autocomplete
from engines.models import Component,Engine,Cluster

class DataEngineComponentAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Component.objects.none()
        engine_id = self.forwarded.get('engine', None)
        if not engine_id:
            return Component.objects.none()
        qs = Engine.objects.get(pk=engine_id).components.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

class DataInstanceEngineAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return models.DataEngine.objects.none()
        cluster_id = self.forwarded.get('cluster', None)
        dataset_id = self.forwarded.get('dataset', None)
        if not cluster_id or not dataset_id:
            return models.DataEngine.objects.none()
        qs = models.DataEngine.objects.filter(
            engine__in = Cluster.objects.get(pk=cluster_id).engines.all(),
            type=models.Dataset.objects.get(pk=dataset_id).type
        ).order_by('-pk')
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

@api_view(['GET'])
def data_state(request):
    today = datetime.now()
    begin_day = today - timedelta(days=365)
    state = {
        'dataset':{},
        'engine':{},
        'instance':{},
        'space':{}
    }
    state['dataset']['owner_cnt']=list(models.Dataset.objects.values('owner__username').annotate(cnt=Count('id')).order_by('-cnt')[0:10])
    state['dataset']['total_cnt']=models.Dataset.objects.all().count()
    state['dataset']['total_size']=models.Dataset.objects.all().aggregate(total_size=Sum('size'))['total_size']
    state['dataset']['public_size']=list(models.Dataset.objects.values('public').annotate(size=Sum('size')))
    state['dataset']['owner_size']=list(models.Dataset.objects.values('owner__username').annotate(size=Sum('size')).order_by('-size')[0:10])
    state['dataset']['month_size']=list(models.Dataset.objects.filter(modified_time__range=(begin_day, today)).values('modified_time__year', 'modified_time__month').annotate(size=Sum('size')).order_by('modified_time__year', 'modified_time__month'))
    state['instance']['dataset_cnt']=list(models.DataInstance.objects.values('dataset__name').annotate(cnt=Count('id')).order_by('-cnt')[0:10])
    state['instance']['owner_cnt']=list(models.DataInstance.objects.values('owner__username').annotate(cnt=Count('id')).order_by('-cnt')[0:10])
    state['instance']['total_cnt']=models.DataInstance.objects.all().count()
    return Response(state)

#TODO finer permission control
class DataSourceViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.DataSourceSerializer
    filter_fields=('public',)
    ordering_fields = '__all__'
    search_fields = ('name','uri','remark','description')
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdminOrPublicReadOnly,)
    # http_method_names = ['get','post','delete','head','options']
    def get_queryset(self):
        queryset = models.DataSource.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class DatasetViewSet(viewsets.ModelViewSet):
    filter_fields=('public','source',)
    ordering_fields = '__all__'
    search_fields = ('name','remark','description')
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdminOrPublicReadOnly,)
    #http_method_names = ['get','post','delete','head','options']
    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return serializers.DatasetReadSerializer
        else:
            return serializers.DatasetSerializer
    def get_queryset(self):
        queryset = models.Dataset.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class DataEngineViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.DataEngineSerializer
    filter_fields=('public',)
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdminOrPublicReadOnly,)
    http_method_names = ['get','post','delete','head','options']
    def get_queryset(self):
        queryset = models.DataEngine.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class DataInstanceViewSet(viewsets.ModelViewSet):
    filter_fields=('space','dataset','engine')
    ordering_fields = '__all__'
    search_fields = ('name','uri_suffix','remark')
    serializer_class = serializers.DataInstanceSerializer
    permission_classes = (IsAuthenticated,permissions.IsOwner,)
    http_method_names = ['get','post','delete','head','options']
    def get_queryset(self):
        queryset = models.DataInstance.objects.filter(owner=self.request.user).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class DataInstanceOperationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.DataInstanceOperationSerializer
    http_method_names = ['get','post','head','options']
    def get_queryset(self):
        queryset = models.DataInstanceOperation.objects.filter(target__owner=self.request.user).order_by('-pk')
        return queryset