from django.urls import re_path, include
from rest_framework import routers
from . import views

ROUTER = routers.DefaultRouter()
ROUTER.register(r'engines', views.EngineViewSet, basename='engine')
ROUTER.register(r'scales', views.ScaleViewSet, basename='scale')
ROUTER.register(r'clusters', views.ClusterViewSet, basename='cluster')
ROUTER.register(r'clusteroperations', views.ClusterOperationViewSet, basename='clusteroperation')

urlpatterns = [
    re_path(r'^', include(ROUTER.urls)),
]
