from django.contrib import admin
from django.db.models import Q, fields
from django.utils.html import format_html
from django.utils.timezone import now
from daa.admin import AutoModelAdmin
from clouds.utils import get_formated_url, get_url
from user.models import Balance
from .models import OPERATION_STATUS
from django.db import transaction

def get_get_prefill_form(self, request, obj=None, **kwargs):
    form = super().get_form(request, obj, **kwargs)
    for fname in request.GET:
        if fname in form.base_fields:
            # form.base_fields[fname].disabled=True
            # form.base_fields[fname].widget=forms.HiddenInput()
            form.base_fields[fname].widget.attrs={
                'readonly': True,
                'style': 'border: none; outline: none;'
            }
    return form
AutoModelAdmin.get_form=get_get_prefill_form

#TODO use staticmodel of_user
def powerful_form_field_queryset_Q(db_field, request):
    if db_field.name == 'cloud':
        return Q(balance__in=request.user.balances())
    model=db_field.remote_field.model
    q=None
    if getattr(model, 'owner', False):
        q = Q(owner=request.user)
        if getattr(model, 'public', False):
            q= (q | Q(public=True))
        if getattr(model, 'enabled', False):
            q= q & Q(enabled=True)
    return q

class OwnershipModelAdmin(AutoModelAdmin):
    # def action_checkbox(self, obj):
    #     u=get_current_user()
    #     if not u.is_superuser and u!=obj.owner: return None
    #     return super().action_checkbox(obj)
    # action_checkbox.short_description=AutoModelAdmin.action_checkbox.short_description
    def has_change_permission(self, request, obj=None):
        return not obj or obj.owner==request.user
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.owner==request.user or request.user.is_superuser
    def get_queryset_Q(self, request):
        return Q(owner=request.user)
    def save_model(self, request, obj, form, change):
        obj.owner = request.user
        obj.save()
    def get_form_field_queryset_Q(self, db_field, request):
        return powerful_form_field_queryset_Q(db_field, request)

class StaticModelAdmin(OwnershipModelAdmin):
    search_fields = ('name','remark')
    list_filter = ('public', 'enabled',
        ('owner', admin.RelatedOnlyFieldListFilter),
    )
    form_fields_exclude=('name',)
    def get_fields(self,request,obj):
        return ('name',) + super().get_fields(request,obj)
    def get_list_display_exclude(self, request, obj=None):
        return ('created_time','name')
    def get_list_display(self, request, obj=None):
        return ('name',)+super().get_list_display(request,obj)
    def get_queryset_Q(self, request):
        return super().get_queryset_Q(request) | (Q(public=True) & Q(enabled=True))
    actions=None

class OperatableAdminMixin(object):
    def action_button(self, obj, op_url):
        ops=obj.get_running_operations()
        if ops.exists(): return ops[0].operation+'ing'
        former=obj.get_former_operation()
        if former and former.status==OPERATION_STATUS.failed.value: return OPERATION_STATUS.failed.value
        if not obj.startable and not obj.stopable: return None
        if obj.stopable:
            op='poweroff'
        else:
            op='start'
        return format_html('<a href="{}" data-id={} data-op={} class="button">{}</a>'.format(op_url,obj.pk,op,op))
    def has_change_permission(self, request, obj=None):
        return False #obj.ready and super().has_change_permission(request,obj)
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.owner==request.user and (obj.ready or obj.deleting) or request.user.is_superuser

class OperationAdmin(AutoModelAdmin):
    list_filter = (
        'operation',
        ('target', admin.RelatedOnlyFieldListFilter),
        'manual',
        'status',
    )
    def _target(self,obj):
        return get_formated_url(obj.target)
    list_display_exclude=('operation','target','tidied','created_time','batch_uuid')
    def get_queryset_Q(self, request):
        return Q(target__owner=request.user)
    def get_form_fields_exclude(self,request,obj=None):
        return ('target',) if obj else ('_target',)
    def get_list_display(self,request,obj=None):
        return ('batch','operation', '_target','script') + super().get_list_display(request,obj)
    def get_readonly_fields(self,request,obj=None):
        return ('_target', 'batch_uuid',) + super().get_readonly_fields(request,obj)
    def get_form_field_queryset_Q(self, db_field, request):
        return powerful_form_field_queryset_Q(db_field, request)
    def has_change_permission(self, request, obj=None):
        return False
    @transaction.atomic
    def rerun(modeladmin, request, queryset):
        for op in queryset.select_for_update():
            op.status=OPERATION_STATUS.running.value
            op.started_time=now()
            op.completed_time=None
            op.save()
            op.execute()
    rerun.short_description = "Re-run selected operations"
    actions=[rerun]

class M2MOperationAdmin(OperationAdmin):
    def sub_operations(self,obj):
        return format_html('<br/>'.join([get_url(sub) for sub in obj.get_sub_operations()]))
    def get_readonly_fields(self, request, obj=None):
        fs=super().get_readonly_fields(request, obj)
        if obj: fs+=('sub_operations',)
        return fs
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.target.owner == request.user or request.user.is_superuser