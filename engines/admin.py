from django.contrib import admin
from . import models
from clouds.base.admin import StaticModelAdmin, OwnershipModelAdmin, OperationAdmin, OperatableAdminMixin, AutoModelAdmin
from clouds.models import Cloud, InstanceBlueprint, InstanceOperation, GroupOperation
from user.models import Balance
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from django import forms
from dal import autocomplete
from user.utils import get_current_user
from clouds.utils import get_url, get_formated_url

admin.site.register(models.Component,StaticModelAdmin)
admin.site.register(models.Engine,StaticModelAdmin)

@admin.register(models.Scale)
class ScaleAdmin(StaticModelAdmin):
    list_filter = ('auto',)+StaticModelAdmin.list_filter
    def get_queryset_Q(self, request):
        return super().get_queryset_Q(request) | (Q(public=True) & Q(enabled=True))
    def get_queryset_Q(self, request):
        balances=Balance.objects.filter(profile__owner=request.user,profile__enabled=True,balance__gt=0)
        available_clouds=Cloud.objects.filter(balance__in=balances).distinct()
        available_blueprints=InstanceBlueprint.objects.filter(cloud__in=available_clouds).distinct()
        excluded_blueprints=InstanceBlueprint.objects.exclude(pk__in=available_blueprints)
        return Q(pk__in=models.Scale.objects.exclude(init_blueprints__in=excluded_blueprints))
        
@admin.register(models.Cluster)
class ClusterAdmin(OwnershipModelAdmin,OperatableAdminMixin):
    class ClusterForm(forms.ModelForm):
        class Meta:
            model = models.Cluster
            fields = ('__all__')
            widgets = {
                'engines': autocomplete.ModelSelect2Multiple(
                    url='clusterengines-autocomplete',
                    forward=['scale']
                ),
            }
    form = ClusterForm
    def access(self, obj):
        if not obj.ready: return None
        return format_html('<a href="{}" target="_blank" class="button">Manage</a>'.format(obj.portal))
    def instances(self,object):
        return format_html('<br/>'.join([get_url(ins) for ins in object.get_instances()]))  
    def action(self, obj):
        if obj.deleting:
            if not get_current_user().is_superuser:
                return 'deleting'
        op_url=reverse('clusteroperation-list')
        return self.action_button(obj,op_url)
    search_fields = ('name','scale__name')+OwnershipModelAdmin.search_fields
    list_filter = (('scale', admin.RelatedOnlyFieldListFilter),)+OwnershipModelAdmin.list_filter
    extra=('access','action','instances')
    def get_list_display_exclude(self, request, obj=None):
        if request.user.is_superuser: return ('instances',)
        return ('owner','deleting','instances')
    def start(modeladmin, request, queryset):
        for cluster in queryset:
            models.ClusterOperation(
                target=cluster,
                operation=models.INSTANCE_OPERATION.start.value,
                status=models.OPERATION_STATUS.running.value
            ).save()
    start.short_description = "Start selected clusters"
    def scale(modeladmin, request, queryset):
        for cluster in queryset:
            cluster.scale_one_step()
    scale.short_description = "Scale out one step"
    def destroy(modeladmin, request, queryset):
        for cluster in queryset:
            cluster.delete()
    destroy.short_description = "Destroy selected clusters"
    actions=[start,scale,destroy]
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(models.ClusterOperation)
class ClusterOperationAdmin(OperationAdmin):
    def related_instance_operations(self,obj):
        return format_html('<br/>'.join([get_url(io) for io in InstanceOperation.objects.filter(batch_uuid=obj.batch_uuid)]))
    def get_readonly_fields(self, request, obj=None):
        fs=super().get_readonly_fields(request, obj)
        if obj: fs+=('related_instance_operations',)
        return fs
    def get_queryset(self, request):
        qs = super().get_queryset(request).order_by('-started_time')
        if request.user.is_superuser: return qs
        return qs.filter(target__owner=request.user)
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.target.owner == request.user or request.user.is_superuser

# @admin.register(models.EngineOperation)
# class EngineOperationAdmin(TargetOperationAdmin):
#     def get_list_display(self, request, obj=None):
#         return ('pilot',)+super().get_list_display(request, obj)
#     def get_readonly_fields(self, request, obj=None):
#         fs=super().get_readonly_fields(request, obj)
#         if not obj:#add
#             return fs
#         return fs+('cluster_operation',)

# admin.site.register(models.PilotOperation,TargetOperationAdmin)