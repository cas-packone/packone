from django.urls import re_path, include
from rest_framework import routers
from . import views

ROUTER = routers.DefaultRouter()
ROUTER.register(r'account', views.AccountViewSet, basename='user')
ROUTER.register(r'profiles', views.ProfileViewSet, basename='profile')
ROUTER.register(r'balance', views.BalanceViewSet, basename='balance')
ROUTER.register(r'credential', views.CredentialViewSet, basename='credential')

urlpatterns = [
    re_path(r'^', include(ROUTER.urls)),
    re_path('info/', views.user_info),
]