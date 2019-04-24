from django.urls import re_path, include
from rest_framework import routers
from . import views

ROUTER = routers.DefaultRouter()
ROUTER.register(r'components', views.ComponentViewSet, base_name='component')
ROUTER.register(r'engines', views.EngineViewSet, base_name='engine')
ROUTER.register(r'scales', views.ScaleViewSet, base_name='scale')
ROUTER.register(r'clusters', views.ClusterViewSet, base_name='cluster')
ROUTER.register(r'clusteroperations', views.ClusterOperationViewSet, base_name='clusteroperation')


urlpatterns = [
    re_path(r'^', include(ROUTER.urls)),
    re_path(
        r'^clusterengines-autocomplete/$',
        views.ClusterEnginesAutocompleteView.as_view(),
        name='clusterengines-autocomplete',
    ),
]
