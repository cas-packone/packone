from django.contrib import admin
from . import models
from clouds.base.admin import StaticModelAdmin, OwnershipModelAdmin, OperationAdmin, OperatableAdminMixin, AutoModelAdmin, M2MOperationAdmin
from clouds.models import Cloud, Group, InstanceBlueprint, InstanceOperation, GroupOperation
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
        return Q(pk__in=request.user.scales())

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
    def get_form_field_queryset_Q(self, db_field, request):
        if db_field.name == 'scale': return Q(pk__in=request.user.scales())
        return None
    def get_queryset_Q(self, request):
        return Q(pk__in=request.user.clusters())

@admin.register(models.ClusterOperation)
class ClusterOperationAdmin(M2MOperationAdmin):
    def get_queryset(self, request):
        qs=models.ClusterOperation.objects.all()
        if request.user.is_superuser: return qs
        return qs.filter(target__in=request.user.clusters()).order_by('-started_time')
    def has_module_permission(self, request):
        return False

@admin.register(models.StepOperation)
class StepOperationAdmin(M2MOperationAdmin):
    list_filter = (
        'operation',
        'manual',
        'status',
    )
    def _target(self,obj):
        return get_formated_url(obj.cluster)
    def get_queryset(self, request):
        qs=models.StepOperation.objects.all()
        if request.user.is_superuser: return qs
        return qs.filter(target__in=request.user.steps()).order_by('-started_time').distinct()
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_view_permission(self, request, obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return True
    def has_module_permission(self, request):
        return True
