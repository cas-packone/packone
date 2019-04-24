from django.urls import re_path, include
from rest_framework import routers
from . import views

ROUTER = routers.DefaultRouter()
ROUTER.register(r'account', views.AccountViewSet, base_name='user')
ROUTER.register(r'profiles', views.ProfileViewSet, base_name='profile')
ROUTER.register(r'balance', views.BalanceViewSet, base_name='balance')
ROUTER.register(r'credential', views.CredentialViewSet, base_name='credential')

urlpatterns = [
    re_path(r'^', include(ROUTER.urls)),
    re_path('info/', views.user_info),
]