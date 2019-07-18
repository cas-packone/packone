from django.contrib import admin
from django.db.models import Q
from . import models
from clouds.admin import AutoModelAdmin, OwnershipModelAdmin
from clouds.models import Cloud

@admin.register(models.Profile)
class ProfileAdmin(OwnershipModelAdmin):
    search_fields = ('organization',)
    def has_delete_permission(self, request, obj=None):
        if not obj: return False
        if obj.enabled: return False
        return True

class EnabledProfileGuardedAdmin(AutoModelAdmin):
    def enabled(self,obj):
        return obj.profile.enabled
    enabled.boolean = True
    extra=('enabled',)
    search_fields = ('profile__organization', 'profile__owner__username')
    def get_queryset_Q(self, request):
        return Q(profile__owner=request.user)

@admin.register(models.Balance)
class BalanceAdmin(EnabledProfileGuardedAdmin):#TODO add balanceZeroException in signal
    search_fields=('cloud__name', 'cloud___driver')+EnabledProfileGuardedAdmin.search_fields
    def has_change_permission(self, request, obj=None):
        return not obj or request.user==obj.cloud.owner
    def has_add_permission(self, request, obj=None):
        return Cloud.objects.filter(owner=request.user).exists()
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.cloud.owner==request.user
    def get_queryset_Q(self, request):
        return super().get_queryset_Q(request)|Q(cloud__owner=request.user)
    def get_form_field_queryset_Q(self, db_field, request):
        if db_field.name=='cloud': return Q(owner=request.user)
        if db_field.name=='profile': return Q(enabled=True) #TODO use text instead of select to choose profile

@admin.register(models.Credential)
class CredentialAdmin(EnabledProfileGuardedAdmin):
    search_fields = ('ssh_user',)+EnabledProfileGuardedAdmin.search_fields
    def has_delete_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request, obj=None):
        return False
   