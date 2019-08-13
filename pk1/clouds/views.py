from dal import autocomplete
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from django.db.models import Q
from . import models
from . import serializers
from . import permissions
from .utils import get_refer_GET_parameter

#TODO: dal can be walked around!!!
class InstanceTemplateAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return models.InstanceTemplate.objects.none()
        cloud_id = self.forwarded.get('cloud', None)
        if not cloud_id:
            return models.InstanceTemplate.objects.none()
        image_id = self.forwarded.get('image', None)
        image=models.Image.objects.get(pk=image_id)
        qs = models.InstanceTemplate.objects.filter(cloud=cloud_id,ram__gte=image.min_ram,disk__gte=image.min_disk,enabled=True).filter(
            Q(owner=self.request.user) | Q(public=True)
        ).order_by('id')
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

class ImageAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return models.Image.objects.none()
        cloud = self.forwarded.get('cloud', None)
        if not cloud:
            return models.Image.objects.none()
        qs = models.Image.objects.filter(cloud=cloud,enabled=True).filter(
            Q(owner=self.request.user) | Q(public=True)
        ).order_by('id')
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

class MountInstanceAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return models.Instance.objects.none()
        volume_id = self.forwarded.get('volume', None)
        if not volume_id:
            return models.Instance.objects.none()
        volume=models.Volume.objects.get(pk=volume_id)
        qs = models.Instance.objects.filter(
            cloud=volume.cloud,
            status__in=[
                models.INSTANCE_STATUS.poweroff.value,
                models.INSTANCE_STATUS.shutdown.value
            ]
        ).order_by('id')
        if not self.request.user.is_superuser:
            qs = qs.filter(owner=self.request.user)
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

class CloudViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = models.Cloud.objects.all()
    serializer_class = serializers.CloudSerializer

class ImageViewSet(viewsets.ModelViewSet):#TODO allow specify image id when post
    filter_fields=('public',)
    http_method_names = ['get','post','delete','head','options']
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdminOrPublicReadOnly,)
    serializer_class = serializers.ImageSerializer
    def get_queryset(self):
        queryset = models.Image.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class InstanceTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.InstanceTemplateSerializer
    queryset = models.InstanceTemplate.objects.all().order_by('-pk')

class InstanceBlueprintViewSet(viewsets.ModelViewSet):
    filter_fields=('public',)
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdminOrPublicReadOnly,)
    http_method_names = ['get','post','delete','head','options']
    serializer_class = serializers.InstanceBlueprintSerializer
    def get_queryset(self):
        queryset = models.InstanceBlueprint.objects.filter(Q(public=True) | Q(owner=self.request.user)).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class InstanceViewSet(viewsets.ModelViewSet):
    filter_fields=('cluster',)
    #TODO diallow to modify specific fields
    permission_classes = (IsAuthenticated,permissions.IsOwnerOrAdmin)
    serializer_class = serializers.InstanceSerializer
    def get_queryset(self):
        queryset = models.Instance.objects.filter(owner=self.request.user).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class InstanceOperationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.InstanceOperationSerializer
    http_method_names = ['get','post','head','options']
    def get_queryset(self):
        queryset = models.InstanceOperation.objects.filter(target__owner=self.request.user).order_by('-pk')
        return queryset

class VolumeViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.VolumeSerializer
    permission_classes = (IsAuthenticated,permissions.IsOwner,)
    def get_queryset(self):
        queryset = models.Volume.objects.filter(owner=self.request.user).order_by('-pk')
        return queryset
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class MountViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.MountSerializer
    http_method_names = ['get','post','delete','head','options']
    def get_queryset(self):
        queryset = models.Mount.objects.filter(volume__owner=self.request.user).order_by('-pk')
        return queryset
