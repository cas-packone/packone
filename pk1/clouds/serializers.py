from rest_framework import serializers
from django.db.models import Q
from . import models

class CloudSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cloud
        fields = ('name', '_driver', 'remark')

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Image
        fields = '__all__'

class ImagePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.Image.objects.filter(Q(public=True) | Q(owner=user))
        return queryset

class InstanceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InstanceTemplate
        fields = '__all__'

class InstanceBlueprintSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    image=ImagePKField()
    class Meta:
        model = models.InstanceBlueprint
        fields = '__all__'

class InstanceBlueprintPKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.InstanceBlueprint.objects.filter(Q(public=True) | Q(owner=user))
        return queryset
        
class InstanceSerializer(serializers.ModelSerializer):
    #TODO linked droplist betweeen cloud and image
    owner = serializers.ReadOnlyField(source='owner.username')
    image=ImagePKField()
    class Meta:
        model = models.Instance
        fields = '__all__'

class InstancePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        qs = models.Instance.objects.all().order_by('-id')
        user = self.context['request'].user
        if not user.is_superuser:
            qs = qs.filter(owner=user)
        return qs

class InstanceOperationSerializer(serializers.ModelSerializer):
    #TODO filter out running instances when perform poweroff op
    target=InstancePKField()
    class Meta:
        model = models.InstanceOperation
        fields = '__all__'

class VolumeSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = models.Volume
        fields = '__all__'

class VolumeUnmountedPKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        qs = models.Volume.objects.filter(mount=None)
        if not user.is_superuser:
            qs = qs.filter(owner=user)
        return qs

class InstanceMountablePKField(serializers.PrimaryKeyRelatedField):#TODO enable frontend filtering based on relatedField
    def get_queryset(self):
        user = self.context['request'].user
        qs = models.Instance.objects.filter(status__in=[
            models.INSTANCE_STATUS.poweroff.value,
            models.INSTANCE_STATUS.shutdown.value
        ])
        if not user.is_superuser:
            qs = qs.filter(owner=user)
        return qs

class MountSerializer(serializers.ModelSerializer):
    volume=VolumeUnmountedPKField()
    instance=InstanceMountablePKField()
    class Meta:
        model = models.Mount
        fields = '__all__'