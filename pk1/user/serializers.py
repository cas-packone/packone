from django.contrib.auth.models import User
from rest_framework import serializers
from . import models

class AccountSerializer(serializers.ModelSerializer):
    last_login = serializers.ReadOnlyField()
    date_joined = serializers.ReadOnlyField()
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'last_login', 'date_joined')

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Profile
        fields = ('id','organization','remark')

class ProfilePKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = models.Profile.objects.filter(account=user)
        return queryset

class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Balance
        fields = ('id','cloud','balance','enabled')

class CredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Credential
        fields = ('id','ssh_user','ssh_public_key','ssh_passwd')
