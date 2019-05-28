from django.urls import re_path,include
from rest_framework import routers
from . import views

ROUTER = routers.DefaultRouter()
ROUTER.register(r'datasources', views.DataSourceViewSet,base_name='datasource')
ROUTER.register(r'datasets', views.DatasetViewSet,base_name='dataset')
ROUTER.register(r'dataengines', views.DataEngineViewSet,base_name='dataengine')
ROUTER.register(r'datainstances', views.DataInstanceViewSet,base_name='datainstance')
ROUTER.register(r'datainstanceoperations', views.DataInstanceOperationViewSet,base_name='datainstanceoperation')

urlpatterns = [
    re_path(r'^', include(ROUTER.urls)),
    re_path(
        r'^datainstanceengine-autocomplete/$',
        views.DataInstanceEngineAutocompleteView.as_view(),
        name='datainstanceengine-autocomplete',
    ),
    re_path('state/', views.data_state),
]