from django.urls import re_path, include
from rest_framework import routers
from . import views

ROUTER = routers.DefaultRouter()
ROUTER.register(r'clouds', views.CloudViewSet)
ROUTER.register(r'images', views.ImageViewSet, basename='image')
ROUTER.register(r'instancetemplates', views.InstanceTemplateViewSet)
ROUTER.register(r'instanceblueprints', views.InstanceBlueprintViewSet, basename='instanceblueprint')
ROUTER.register(r'instances', views.InstanceViewSet, basename='instance')
ROUTER.register(r'instanceoperations', views.InstanceOperationViewSet, basename='instanceoperation')
ROUTER.register(r'volumes', views.VolumeViewSet, basename='volume')
ROUTER.register(r'mounts', views.MountViewSet, basename='mount')

urlpatterns = [
    re_path(r'^', include(ROUTER.urls)),
    re_path(
        r'^instancetemplate-autocomplete/$',
        views.InstanceTemplateAutocompleteView.as_view(),
        name='instancetemplate-autocomplete',
    ),
    re_path(
        r'^image-autocomplete/$',
        views.ImageAutocompleteView.as_view(),
        name='image-autocomplete',
    ),
    re_path(
        r'^mountinstance-autocomplete/$',
        views.MountInstanceAutocompleteView.as_view(),
        name='mountinstance-autocomplete',
    ),
]
