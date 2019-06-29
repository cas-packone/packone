"""packone URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

admin.site.site_header = 'PackOne Console' # default: "Django Administration"
admin.site.index_title = 'Dashboard' # default: "Site administration"
admin.site.site_title = 'PackOne Console' # default: "Django site admin"
admin.site.site_url = None

urlpatterns = [
    re_path(r'^', admin.site.urls),
    path('api/user/', include('user.urls')),
    path('api/clouds/', include('clouds.urls')),
    path('api/engines/', include('engines.urls')),
    path('api/data/', include('data.urls')),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root':settings.STATIC_ROOT}),
    re_path(r'^api/token/$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    re_path(r'^api/token/refresh/$', TokenRefreshView.as_view(), name='token_refresh'),
]