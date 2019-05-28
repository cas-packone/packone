from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from django.db.models import Q, IntegerField, Case, When, Count
from clouds import permissions
from clouds.models import Image
from .models import Scale
from . import models
from . import serializers
from dal import autocomplete

class EngineViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.EngineSerializer
    filter_fields=('public',)
    permission_classes = (IsAuthenticated, permissions.IsOwnerOrAdminOrPublicReadOnly,)
    def get_queryset(self):
        queryset = models.Engine.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ScaleViewSet(viewsets.ModelViewSet):
    filter_fields=('public',)
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdminOrPublicReadOnly,)
    http_method_names = ['get','post','delete','head','options']
    serializer_class = serializers.ScaleSerializer
    def get_queryset(self):
        queryset = models.Scale.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
class ClusterViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,permissions.IsOwner,)
    serializer_class = serializers.ClusterSerializer
    def get_queryset(self):
        queryset = models.Cluster.objects.filter(owner=self.request.user).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ClusterOperationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ClusterOperationSerializer
    http_method_names = ['get','post','head','options']
    def get_queryset(self):
        queryset = models.ClusterOperation.objects.filter(target__owner=self.request.user).order_by('-pk')
        return queryset