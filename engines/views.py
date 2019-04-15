from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from django.db.models import Q, IntegerField, Case, When, Count
from clouds import permissions
from clouds.models import Image
from .models import Scale
from . import models
from . import serializers
from dal import autocomplete

def get_available_engines(scale_id):
    scale=Scale.objects.get(pk=scale_id)
    imgs=Image.objects.filter(
        instance_blueprints__in=scale.init_blueprints.all()
    ).distinct()
    hosted_components=models.Component.objects.annotate(
        num_imgs=Count('images')
    ).filter(
        num_imgs=len(imgs)
    ).exclude(
        images__in=Image.objects.exclude(pk__in=imgs)
    )
    return models.Engine.objects.exclude(
        components__in=models.Component.objects.exclude(pk__in=hosted_components)
    ).order_by('id')

class ClusterEnginesAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return models.Engine.objects.none()
        scale_id = self.forwarded.get('scale', None)
        if not scale_id:
            return models.Engine.objects.none()
        qs = get_available_engines(scale_id)
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

class ComponentViewSet(viewsets.ModelViewSet):
    filter_fields=('public',)
    permission_classes = (IsAuthenticated, permissions.IsOwnerOrAdminOrPublicReadOnly,)
    serializer_class = serializers.ComponentSerializer
    def get_queryset(self):
        queryset = models.Component.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-id')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class EngineViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.EngineSerializer
    filter_fields=('public',)
    permission_classes = (IsAuthenticated, permissions.IsOwnerOrAdminOrPublicReadOnly,)
    def get_queryset(self):
        queryset = models.Engine.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-id')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ScaleViewSet(viewsets.ModelViewSet):
    filter_fields=('public',)
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdminOrPublicReadOnly,)
    http_method_names = ['get','post','delete','head','options']
    serializer_class = serializers.ScaleSerializer
    def get_queryset(self):
        queryset = models.Scale.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-id')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
class ClusterViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,permissions.IsOwner,)
    serializer_class = serializers.ClusterSerializer
    def get_queryset(self):
        queryset = models.Cluster.objects.filter(owner=self.request.user).order_by('-id')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ClusterOperationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ClusterOperationSerializer
    http_method_names = ['get','post','head','options']
    def get_queryset(self):
        queryset = models.ClusterOperation.objects.filter(target__owner=self.request.user).order_by('-id')
        return queryset