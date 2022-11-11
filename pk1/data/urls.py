from django.urls import re_path,include
from rest_framework import routers
from . import views

ROUTER = routers.DefaultRouter()
ROUTER.register(r'datasources', views.DataSourceViewSet,basename='datasource')
ROUTER.register(r'datasets', views.DatasetViewSet,basename='dataset')
ROUTER.register(r'dataengines', views.DataEngineViewSet,basename='dataengine')
ROUTER.register(r'datainstances', views.DataInstanceViewSet,basename='datainstance')
ROUTER.register(r'datainstanceoperations', views.DataInstanceOperationViewSet,basename='datainstanceoperation')

urlpatterns = [
    re_path(r'^', include(ROUTER.urls)),
    re_path(
        r'^datainstanceengine-autocomplete/$',
        views.DataInstanceEngineAutocompleteView.as_view(),
        name='datainstanceengine-autocomplete',
    ),
]
