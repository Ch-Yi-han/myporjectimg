"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from myapp import views
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path('index/',views.index,name='index'),
    path('menu/',views.menu,name='menu'),
    path('user_login/',views.user_login,name='user_login'),
    path('register/',views.register,name='register'),
    path('logout/', views.logout, name='logout'),
    path('forgot_password/', views.forgot_password_request, name='forgot_password_request'),
    path('verify_code/', views.verify_code, name='verify_code'),
    path('reset_password/',views.reset_password, name='reset_password'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)