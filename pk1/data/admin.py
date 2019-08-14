from django.contrib import admin
from . import models
from clouds.base.admin import StaticModelAdmin, OwnershipModelAdmin, OperatableAdminMixin, OperationAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django import forms
from django.db.models import Q
from dal import autocomplete
from user.utils import get_current_user, get_space

@admin.register(models.DataEngine)
class DataEngineAdmin(StaticModelAdmin):
    search_fields = ('description',)+StaticModelAdmin.search_fields
    
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
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['cluster'].widget = forms.HiddenInput()
            self.fields['cluster'].initial = get_space().pk
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
        if not obj.ready or not obj.cluster.ready: return None
        url=obj.cluster.portal.split('//')[-1].split(':')[0]
        return format_html('<a href="{}" type="{}" target="_blank" class="button">Query</a>'.format(url, obj.dataset.type_name))
    extra=('uri','query')#,'action'
    search_fields = ('name', 'dataset__name', 'cluster__name', 'engine__name')+OwnershipModelAdmin.search_fields
    list_filter = (
        ('dataset', admin.RelatedOnlyFieldListFilter),
        ('engine', admin.RelatedOnlyFieldListFilter),
        ('cluster', admin.RelatedOnlyFieldListFilter),
    )+OwnershipModelAdmin.list_filter
    def get_list_display_exclude(self, request, obj=None):
        if request.user.is_superuser: 
            return ()
        return ('owner','deleting')
    def get_queryset_Q(self, request):
        return (super().get_queryset_Q(request)) and Q(cluster=get_space())
    def response_add(self, request, obj, post_url_continue=None):
        url=reverse("admin:data_datainstance_changelist")
        space=get_space()
        if space: url='/space/{}'.format(space.pk)+url
        return redirect(url)

@admin.register(models.DataInstanceOperation)
class DataInstanceOperationAdmin(OperationAdmin):
    def get_list_display(self,request,obj=None):
        return super().get_list_display(request,obj)+('log',)
    def get_queryset_Q(self, request):
        return super().get_queryset_Q(request) and Q(target__cluster=get_space())