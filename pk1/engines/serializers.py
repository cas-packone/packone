from rest_framework import serializers
from django.db.models import Q
from clouds.serializers import ImagePKField, InstanceBlueprintPKField
from . import models

class EngineSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = models.Engine
        fields = '__all__'

class EnginePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.Engine.objects.filter(Q(public=True) | Q(owner=user))
        return queryset

class ScaleSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    init_blueprints = InstanceBlueprintPKField(many=True)
    step_blueprints = InstanceBlueprintPKField(many=True)
    instance_quantity = serializers.ReadOnlyField()
    cpu_quantity = serializers.ReadOnlyField()
    mem_quantity = serializers.ReadOnlyField()
    volume_capacity = serializers.ReadOnlyField()
    class Meta:
        model = models.Scale
        fields = '__all__'

class ScalePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.Scale.objects.filter(Q(public=True) | Q(owner=user))
        return queryset

class ClusterPKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        qs = models.Cluster.objects.all()
        if not user.is_superuser:
            qs = qs.filter(owner=user)
        return qs

class ClusterSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    scale=ScalePKField()
    engines=EnginePKField(many=True)
    portal = serializers.ReadOnlyField()
    class Meta:
        model = models.Cluster
        fields = '__all__'

class ClusterOperationSerializer(serializers.ModelSerializer):
    target=ClusterPKField()
    class Meta:
        model = models.ClusterOperation
        fields = '__all__' 