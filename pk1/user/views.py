from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from . import models
from . import serializers

def _get_enabled_profile(request):
    return models.Profile.objects.filter(account=request.user,enabled=True)[0]
    
@api_view(['GET'])
def user_info(request):
    profile = _get_enabled_profile(request)
    roles=[]
    if profile.account.is_active:
        roles.append('user')
    if profile.account.is_superuser:
        roles.append('admin')
    return Response({
        "organization": profile.organization,
        "name": profile.account.first_name if profile.account.first_name else profile.account.username,
        "roles": roles,
        "avatar": profile.avatar
        })

class AccountViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    serializer_class = serializers.AccountSerializer
    http_method_names = ['get','post','delete','head','options']
    def get_queryset(self):
        queryset = User.objects.filter(pk=self.request.user.pk).order_by('-date_joined')
        return queryset

class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ProfileSerializer
    def get_queryset(self):
        queryset = models.Profile.objects.filter(account=self.request.user).order_by('-id')
        return queryset
    def perform_create(self, serializer):
        serializer.save(account=self.request.user)

class BalanceViewSet(viewsets.ReadOnlyModelViewSet):#TODO do we need add permission_classes = (IsAuthenticated, permissions.IsOwner,)
    serializer_class = serializers.BalanceSerializer
    def get_queryset(self):
        queryset = models.Balance.objects.filter(profile__account=self.request.user)
        return queryset

class CredentialViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CredentialSerializer
    def get_queryset(self):
        queryset = models.Credential.objects.filter(profile=_get_enabled_profile(self.request))
        return queryset
    def perform_create(self, serializer):
        serializer.save(profile=_get_enabled_profile(self.request))