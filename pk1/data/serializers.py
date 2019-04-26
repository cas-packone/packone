from . import models
from rest_framework import serializers
from django.db.models import Q
from engines.serializers import ComponentPKField,ClusterPKField
from data.models import DATASET_TYPE

class DataSourceSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = models.DataSource
        fields = '__all__'

class DataSourcePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.DataSource.objects.filter(Q(public=True) | Q(owner=user))
        return queryset

class DatasetSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = models.Dataset
        fields = '__all__'

class DatasetReadSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    type_name = serializers.ReadOnlyField()
    def to_representation(self, obj):
        # get the original representation
        ret = super(DatasetReadSerializer, self).to_representation(obj)
        if obj.owner!=self.context['request'].user:
            ret.pop('uri')
            ret.pop('remedy_script')
        return ret
    class Meta:
        model = models.Dataset
        fields = '__all__'

class DatasetPKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.Dataset.objects.filter(Q(public=True) | Q(owner=user))
        return queryset

class DataEngineSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    component = ComponentPKField()
    class Meta:
        model = models.DataEngine
        fields = '__all__'
        
class DataEnginePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.DataEngine.objects.filter(Q(public=True) | Q(owner=user))
        return queryset

class DataEngineSpacePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.DataEngine.objects.filter(Q(public=True) | Q(owner=user))
        return queryset

class DataInstanceSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    cluster = ClusterPKField()
    dataset=DatasetPKField()
    engine=DataEnginePKField()#filter out the space unselected engines
    uri_elected = serializers.ReadOnlyField()
    uri_alive = serializers.ReadOnlyField()
    uri_total = serializers.ReadOnlyField()
    status_name = serializers.ReadOnlyField()
    class Meta:
        model = models.DataInstance
        fields = '__all__'

class DataInstancePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        qs = models.DataInstance.objects.all()
        if not user.is_superuser:
            qs = qs.filter(owner=user)
        return qs

class DataInstanceOperationSerializer(serializers.ModelSerializer):
    target=DataInstancePKField()
    class Meta:
        model = models.DataInstanceOperation
        fields = '__all__'