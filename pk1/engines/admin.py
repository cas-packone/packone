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

@admin.register(models.Stack)
class StackAdmin(StaticModelAdmin):
    list_filter = ('_driver',)+StaticModelAdmin.list_filter
    def import_engine(modeladmin, request, queryset):
        for stack in queryset:
            stack.import_engine()
    import_engine.short_description = "Refresh engines from selected stacks"
    actions = [import_engine]

@admin.register(models.Engine)
class EngineAdmin(StaticModelAdmin):
    pass

@admin.register(models.Scale)
class ScaleAdmin(StaticModelAdmin):
    list_filter = ('auto',)+StaticModelAdmin.list_filter
    def get_queryset_Q(self, request):
        return Q(pk__in=request.user.scales())

@admin.register(models.Cluster)
class ClusterAdmin(OwnershipModelAdmin,OperatableAdminMixin):
    def access(self, obj):
        if not obj.ready: return None
        return format_html('<a href="{}" target="_blank" class="button">Manage</a>'.format(obj.portal))
    def instances(self,object):
        return format_html('<br/>'.join([get_url(ins) for ins in object.get_instances()]))
    search_fields = ('name','scale__name')+OwnershipModelAdmin.search_fields
    list_filter = (('scale', admin.RelatedOnlyFieldListFilter),)+OwnershipModelAdmin.list_filter
    extra=('access','instances')
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
    def stop(modeladmin, request, queryset):
        for cluster in queryset:
            models.ClusterOperation(
                target=cluster,
                operation=models.INSTANCE_OPERATION.poweroff.value,
                status=models.OPERATION_STATUS.running.value
            ).save()
    stop.short_description = "Stop selected clusters"
    def materialize(modeladmin, request, queryset):
        for cluster in queryset:
            if not cluster.name.startswith('bootstrap.'): continue
            for ins in cluster.get_instances():
                try:
                    ins.cloud.driver.instances.get(str(ins.uuid)).create_image(ins.image.name.replace('-bootstrap',''))
                except Exception as e:
                    print(e)
            ins.cloud.import_image()
            image_master1=ins.cloud.image_set.get(name='packone-master1')
            image_master2=ins.cloud.image_set.get(name='packone-master2')
            image_slave=ins.cloud.image_set.get(name='packone-slave')
            blueprint_master1, created=ins.cloud.instanceblueprint_set.get_or_create(
                name='packone-master1',
                cloud=ins.cloud,
                template=ins.template,
                image=image_master1,
                volume_capacity=500,
                remark='auto created',
                owner=ins.owner
            )
            blueprint_master2, created=ins.cloud.instanceblueprint_set.get_or_create(
                name='packone-master2',
                cloud=ins.cloud,
                template=ins.template,
                image=image_master2,
                volume_capacity=500,
                remark='auto created',
                owner=ins.owner
            )
            blueprint_slave, created=ins.cloud.instanceblueprint_set.get_or_create(
                name='packone-slave',
                cloud=ins.cloud,
                template=ins.template,
                image=image_slave,
                volume_capacity=500,
                remark='auto created',
                owner=ins.owner
            )
            from .utils import remedy_scale_ambari_fast_init, remedy_scale_ambari_fast_scale_out, remedy_scale_ambari_fast_scale_in
            s, created=models.Scale.objects.get_or_create(
                name='packone.{}'.format(ins.cloud.name),
                _remedy_script=remedy_scale_ambari_fast_init(),
                _remedy_script_scale_out=remedy_scale_ambari_fast_scale_out(),
                _remedy_script_scale_in=remedy_scale_ambari_fast_scale_in(),
                owner=ins.owner
            )
            if created:
                s.init_blueprints.add(*(blueprint_master1, blueprint_master2, blueprint_slave))
                s.step_blueprints.add(*(blueprint_slave,))
    materialize.short_description = "Materialize the cluster as a scale"
    def scale_out(modeladmin, request, queryset):
        for cluster in queryset:
            cluster.scale_one_step()
    scale_out.short_description = "Scale out one step"
    def scale_in(modeladmin, request, queryset):
        for cluster in queryset:
            cluster.steps.last().delete()
    scale_in.short_description = "Scale in one step"
    def destroy(modeladmin, request, queryset):
        for cluster in queryset:
            cluster.delete()
    destroy.short_description = "Destroy selected clusters"
    actions=[start,stop,materialize,scale_out,scale_in,destroy]
    def has_delete_permission(self, request, obj=None):
        return False
    def get_form_field_queryset_Q(self, db_field, request):
        if db_field.name == 'scale': return Q(pk__in=request.user.scales())
        return None
    def get_queryset_Q(self, request):
        return Q(pk__in=request.user.clusters())
    
@admin.register(models.ClusterOperation)
class ClusterOperationAdmin(M2MOperationAdmin):
    def has_module_permission(self, request):
        return False

@admin.register(models.StepOperation)
class StepOperationAdmin(M2MOperationAdmin):
    def _target(self,obj):
        return  format_html(get_url(obj.cluster)+'/'+get_url(obj.target))
    def get_queryset_Q(self, request):
        return Q(target__in=request.user.steps()) & ~Q(status=models.OPERATION_STATUS.success.value)
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
