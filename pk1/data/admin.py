from django.contrib import admin
from . import models
from clouds.base.admin import StaticModelAdmin, OwnershipModelAdmin, OperatableAdminMixin, OperationAdmin
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from django.db.models import Q
from dal import autocomplete
from user.utils import get_current_user

@admin.register(models.DataEngine)
class DataEngineAdmin(StaticModelAdmin):
    search_fields = ('description',)+StaticModelAdmin.search_fields
    class DataEngineForm(forms.ModelForm):
        class Meta:
            model = models.DataEngine
            fields = ('__all__')
            widgets = {
                'component': autocomplete.ModelSelect2(
                    url='dataenginecomponent-autocomplete',
                    forward=['engine']
                ),
            }
    form = DataEngineForm

@admin.register(models.DataSource)
class DataSourceAdmin(StaticModelAdmin):
    search_fields = ('description',)+StaticModelAdmin.search_fields
        
@admin.register(models.Dataset)
class DatasetAdmin(StaticModelAdmin):
    search_fields = ('description',)+StaticModelAdmin.search_fields
    def action(self,obj):
        return format_html('<a href="{}?dataset={}" class="button">Load</a>'.format(reverse('admin:data_datainstance_add'),obj.pk))
    extra=('action',)

@admin.register(models.DataInstance)
class DataInstanceAdmin(OwnershipModelAdmin,OperatableAdminMixin):
    class DataInstanceForm(forms.ModelForm):
        class Meta:
            model = models.DataInstance
            fields = ('__all__')
            widgets = {
                'engine': autocomplete.ModelSelect2(
                    url='datainstanceengine-autocomplete',
                    forward=['dataset','cluster']
                ),
            }
    form = DataInstanceForm
    def query(self, obj):
        # if not obj.ready: return None
        return format_html('<a href="{}" target="_blank" class="button">Query</a>'.format('obj.uri_elected'))
    def action(self, obj):
        if obj.deleting:
            if not get_current_user().is_superuser: 
                return 'deleting'
        op_url=reverse('datainstanceoperation-list')
        return self.action_button(obj,op_url)
    extra=('uri','action','query')
    search_fields = ('name', 'dataset__name', 'cluster__name', 'engine__name')+OwnershipModelAdmin.search_fields
    list_filter = (
        ('dataset', admin.RelatedOnlyFieldListFilter),
        ('engine', admin.RelatedOnlyFieldListFilter),
        ('cluster', admin.RelatedOnlyFieldListFilter),
    )+OwnershipModelAdmin.list_filter
    
@admin.register(models.DataInstanceOperation)
class DataInstanceOperationAdmin(OperationAdmin):
    def get_list_display(self,request,obj=None):
        return super().get_list_display(request,obj)+('log',)