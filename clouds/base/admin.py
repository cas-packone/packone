from django.contrib import admin
from django.db.models import Q, fields
from django.utils.html import format_html
from clouds.utils import get_formated_url, get_url
from user.models import Balance
from .models import OPERATION_STATUS

class AutoModelAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model,admin_site)
        fs_head=[]
        fs_tail=[]
        fs_readonly=[]
        fs_editable=[]
        fs_list_display=[]
        fs_all=self.model._meta.get_fields()
        base_dict=self.model.__bases__[0].__dict__
        for f in fs_all:
            if f.auto_created or not f.concrete: continue
            if not f.editable: fs_readonly.append(f)
            if f.name not in base_dict: fs_head.append(f)
            else: fs_tail.append(f)
        self.head_fields=tuple(f.name for f in fs_head)
        self.tail_fields=tuple(f.name for f in fs_tail)
        for f in fs_head+fs_tail:
            if f.editable: fs_editable.append(f)
            if type(f) in (fields.TextField,fields.UUIDField,fields.related.ManyToManyField): continue
            fs_list_display.append(f)
        self.auto_readonly_fields=tuple(f.name for f in fs_readonly)
        self.editable_fields=tuple(f.name for f in fs_editable)
        self.auto_list_display=tuple(f.name for f in fs_list_display)
    extra=()
    form_fields_exclude=()
    list_display_exclude=()
    queryset_Q=None
    form_field_queryset_Q=None
    def get_extra(self, request, obj=None):
        return self.extra
    def get_form_fields_exclude(self, request, obj=None):
        return self.form_fields_exclude
    def get_list_display_exclude(self, request, obj=None):
        return self.list_display_exclude
    def get_queryset_Q(self, request):
        return self.queryset_Q
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser: return qs
        q=self.get_queryset_Q(request)
        if q: qs = qs.filter(q)
        return qs.distinct()
    def get_fields(self, request, obj=None):
        form_excls=self.get_form_fields_exclude(request,obj)
        excls=self.get_exclude(request,obj)
        if excls: form_excls+=excls
        if self.fields: 
            fs=fields
        else:
            fs=self.editable_fields
            if obj: fs+=self.get_readonly_fields(request, obj)
        return tuple(f for f in fs if f not in form_excls) if form_excls else fs
    def get_readonly_fields(self, request, obj=None):
        if not obj: return ()
        if self.readonly_fields: return self.readonly_fields
        return self.auto_readonly_fields+self.get_extra(request,obj)
    def get_list_display(self, request, obj=None):
        if self.list_display[0] != '__str__': return self.list_display
        lde=self.get_list_display_exclude(request,obj)
        fs=self.auto_list_display+self.get_extra(request,obj)
        if lde: return tuple(f for f in fs if f not in lde)
        return fs
    def get_form_field_queryset_Q(self, db_field, request):
        return self.form_field_queryset_Q
    def _formfield_filter(self, db_field, request, call_back, **kwargs):
        q=self.get_form_field_queryset_Q(db_field, request)
        if q: kwargs["queryset"]=db_field.remote_field.model.objects.filter(q).distinct()
        return call_back(db_field, request, **kwargs)
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        return self._formfield_filter(db_field, request, super().formfield_for_foreignkey, **kwargs)
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        return self._formfield_filter(db_field, request, super().formfield_for_manytomany, **kwargs)
    def get_form(self, request, obj=None, **kwargs):
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
    def get_form_fields_exclude(self,request,obj=None):
        return ('target',) if obj else ('_target',)
    def get_list_display(self,request,obj=None):
        return ('operation', '_target',) + super().get_list_display(request,obj)
    def get_readonly_fields(self,request,obj=None):
        return ('_target', 'batch_uuid',) + super().get_readonly_fields(request,obj)
    def get_form_field_queryset_Q(self, db_field, request):
        return powerful_form_field_queryset_Q(db_field, request)
    def has_change_permission(self, request, obj=None):
        return False

class M2MOperationAdmin(OperationAdmin):
    def sub_operations(self,obj):
        return format_html('<br/>'.join([get_url(sub) for sub in obj.get_sub_operations()]))
    def get_readonly_fields(self, request, obj=None):
        fs=super().get_readonly_fields(request, obj)
        if obj: fs+=('sub_operations',)
        return fs
    def get_queryset(self, request):
        qs = super().get_queryset(request).order_by('-started_time')
        if request.user.is_superuser: return qs
        return qs.filter(target__owner=request.user)
    def has_delete_permission(self, request, obj=None):
        return not obj or obj.target.owner == request.user or request.user.is_superuser