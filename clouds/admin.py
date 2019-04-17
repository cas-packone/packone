from django.contrib import admin
from django.db.models import Q
from dal import autocomplete
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from user.models import Balance
from user.utils import get_current_user
from .utils import get_url, get_formated_url
from .base.admin import AutoModelAdmin, StaticModelAdmin, OwnershipModelAdmin, OperatableAdminMixin, OperationAdmin, powerful_form_field_queryset_Q
from . import models
    
@admin.register(models.Cloud)
class CloudAdmin(StaticModelAdmin):
    list_filter = ('_driver',)+StaticModelAdmin.list_filter
    def get_exclude(self, request, obj=None):
        if obj and obj.owner!=request.user:
            return ('_platform_credential','_instance_credential')
        return ()

class CloudStaticModelAdmin(StaticModelAdmin):
    search_fields = ('cloud__name',)+StaticModelAdmin.search_fields
    list_filter = (
        ('cloud', admin.RelatedOnlyFieldListFilter),
    )+StaticModelAdmin.list_filter
    def get_queryset_Q(self, request):
        return (super().get_queryset_Q(request)) & (Q(cloud__in=request.user.clouds()) | Q(cloud__owner=request.user))
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.owner==request.user or obj.cloud.owner == request.user

@admin.register(models.Image)
class ImageAdmin(CloudStaticModelAdmin):
    class ImageForm(forms.ModelForm):
        class Meta:
            model = models.Image
            fields = ('__all__')
            widgets = {
                'parent': autocomplete.ModelSelect2(
                    url='image-autocomplete',
                    forward=['cloud']
                )
            }
    form = ImageForm
    def clone(self,obj):
        return format_html('<a href="{}?access_id={image.access_id}&cloud={image.cloud.pk}&parent={image.pk}" class="button">Clone</a>'.format(reverse('admin:clouds_image_add'),image=obj))
    def launch(self,obj):
        return format_html('<a href="{}?cloud={image.cloud.pk}&image={image.pk}" class="button">Launch</a>'.format(reverse('admin:clouds_instance_add'),image=obj)) 
    extra=('clone','launch')
    def get_list_display_exclude(self, request, obj=None):
        return ('access_id',)+super().get_list_display_exclude(request,obj)

@admin.register(models.InstanceTemplate)
class InstanceTemplateAdmin(CloudStaticModelAdmin):
    def get_list_display_exclude(self, request, obj=None):
        return ('access_id',)+super().get_list_display_exclude(request,obj)
    def has_add_permission(self, request, obj=None):
        if models.Cloud.objects.filter(owner=request.user).exists(): return True
        return False
    def get_form_field_queryset_Q(self, db_field, request):
        return Q(owner=request.user)

#TODO use css and js to move drop down list actions to list and disable operate non-public items
@admin.register(models.InstanceBlueprint)
class InstanceBlueprintAdmin(CloudStaticModelAdmin):
    search_fields = ('template__name', 'image__name')+CloudStaticModelAdmin.search_fields
    list_filter = (
        ('template', admin.RelatedOnlyFieldListFilter),
        ('image', admin.RelatedOnlyFieldListFilter),
    )+CloudStaticModelAdmin.list_filter
    #TODO filter by cloud
    def launch(modeladmin, request, queryset):
        for ib in queryset:
            ib.launch(request.user)
    launch.short_description = "Launch resources from selected blueprints"
    actions = [launch]

@admin.register(models.Instance)
class InstanceAdmin(OwnershipModelAdmin,OperatableAdminMixin):
    class InstanceForm(forms.ModelForm):
        class Meta:
            model = models.Instance
            fields = ('__all__')
            widgets = {
                'template': autocomplete.ModelSelect2(
                    url='instancetemplate-autocomplete',
                    forward=['cloud']
                ),
                'image': autocomplete.ModelSelect2(
                    url='image-autocomplete',
                    forward=['cloud']
                )
            }
    form = InstanceForm
    def action(self, obj):
        if obj.deleting:
            if not get_current_user().is_superuser and obj.cloud.owner!=get_current_user(): 
                return 'deleting'
        op_url=reverse('instanceoperation-list')
        return self.action_button(obj,op_url)
    search_fields = ('cloud__name','cloud__name','template__name', 'image__name', 'hostname', 'ipv4', 'ipv6', 'remark')
    list_filter = (
        ('cloud', admin.RelatedOnlyFieldListFilter),
        ('template', admin.RelatedOnlyFieldListFilter),
        ('image', admin.RelatedOnlyFieldListFilter),
        'status',
    )
    extra=('action',)
    def get_queryset_Q(self, request):
        return super().get_queryset_Q(request) | Q(cloud__in=models.Cloud.objects.filter(owner=request.user))
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.owner==request.user and (obj.ready or obj.deleting) or obj.cloud.owner == request.user
    
@admin.register(models.Volume)
class VolumeAdmin(OwnershipModelAdmin):
    def mounted_to(self,obj):
        return obj.mount.instance.ipv4, obj.mount.point
    def action(self,obj):
        if obj.deleting:
            if not get_current_user().is_superuser and obj.cloud.owner!=get_current_user(): 
                return 'deleting'
        ops=obj.get_running_operations()
        if ops.exists(): return 'mounting'
        if obj.umountable and obj.mount.instance.umountable:
            return format_html('<a href="{}" umount class="button">Umount</a>'.format(reverse('mount-detail',kwargs={'pk':obj.mount.pk})))
        if obj.mountable:
            return format_html('<a href="{}?volume={}" class="button">Mount</a>'.format(reverse('admin:clouds_mount_add'),obj.pk))
    search_fields = ('cloud__name','cloud__name','capacity','remark')
    list_filter = (('cloud', admin.RelatedOnlyFieldListFilter),'status')
    extra=('mounted_to','action')
    def get_list_display_exclude(self, request, obj=None):
        if request.user.is_superuser or models.Cloud.objects.filter(owner=request.user).exists(): 
            return ()
        return ('owner','deleting')
    def get_queryset_Q(self, request):
        return super().get_queryset_Q(request) | Q(cloud__in=models.Cloud.objects.filter(owner=request.user))
    def has_change_permission(self, request, obj=None):
        return False #obj.ready and super().has_change_permission(request,obj)
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.owner==request.user and (obj.ready or obj.deleting) or obj.cloud.owner == request.user
        
@admin.register(models.Mount)
class MountAdmin(AutoModelAdmin):
    class MountForm(forms.ModelForm):
        class Meta:
            model = models.Mount
            fields = ('__all__')
            widgets = {
                'instance': autocomplete.ModelSelect2(
                    url='mountinstance-autocomplete',
                    forward=['volume']
                ),
            }
    form = MountForm
    search_fields = ['instance__ipv4']
    def get_queryset_Q(self, request):
        return Q(volume__owner=request.user) | Q(volume__cloud__in=models.Cloud.objects.filter(owner=request.user))
    def has_change_permission(self, request, obj=None):
        return False
    def has_module_permission(self, request):
        if not request.user.is_authenticated: return False
        if request.user.is_superuser: return True
        if models.Cloud.objects.filter(owner=request.user).exists(): return True
        return False
    def response_add(self, request, obj, post_url_continue=None):
        return redirect(reverse("admin:clouds_volume_changelist"))
    def delete_view(self, request, object_id, extra_context=None):
        m=models.Mount.objects.get(pk=object_id)
        if not m.instance.umountable and request.user!=m.instance.cloud.owner:
            messages.error(request, 'not umountable instance.')
            return redirect('../..')
        return super().delete_view(request, object_id, extra_context)
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        if request.method == "POST" and getattr(response,'context_data',False):
            if "deletable_objects" in response.context_data:
                not_umountables=[]
                for m in response.context_data["queryset"]:
                    if not m.instance.umountable and request.user!=m.instance.cloud.owner:
                        not_umountables.append(m.instance.ipv4)
                if not_umountables:
                    messages.error(request, str(not_umountables)+' are not in umountable status')
                    return redirect('.')
        return response
    def get_form_field_queryset_Q(self, db_field, request):
        return powerful_form_field_queryset_Q(db_field, request)
    def has_change_permission(self, request, obj=None):
        return False #not obj or obj.ready and obj.volume.owner == request.user
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.volume.cloud.owner == request.user or (obj.instance.deleting or obj.ready) and obj.volume.owner == request.user

@admin.register(models.InstanceOperation)
class InstanceOperationAdmin(OperationAdmin):
    def get_list_display(self,request,obj=None):
        return super().get_list_display(request,obj)+('log',)
    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            Q(target__owner=request.user)|Q(target__cloud__in=models.Cloud.objects.filter(owner=request.user))
        ).order_by('-started_time')
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.target.owner == request.user or obj.target.cloud.owner == request.user
    def rerun(modeladmin, request, queryset):
        for op in queryset:
            op.execute()
    rerun.short_description = "Re-run selected operations"
    actions=[rerun]

@admin.register(models.Group)
class GroupAdmin(OwnershipModelAdmin,OperatableAdminMixin):
    def get_list_display_exclude(self, request, obj=None):
        if request.user.is_superuser: return ()
        return ('owner','deleting',)
    def destroy(modeladmin, request, queryset):
        for group in queryset:
            group.delete()
    destroy.short_description = "Destroy selected groups"
    actions=[destroy]
    def has_change_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_module_permission(self, request):
        if request.user.is_superuser: return True
        return False

@admin.register(models.GroupOperation)
class GroupOperationAdmin(OperationAdmin):
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
        return not obj or obj.target.owner == request.user or obj.target.cloud.owner == request.user
    def has_module_permission(self, request):
        if request.user.is_superuser: return True
        return False