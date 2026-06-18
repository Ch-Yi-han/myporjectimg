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
    path('order_online/',views.order_online,name='order_online'),
    path('order_history/',views.order_history,name='order_history'),
    path('view_cart/',views.view_cart,name='view_cart'),
    path('update_cart_quantity/<int:item_id>/<str:action>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('delete_order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('go_to_pay/<int:order_id>/', views.go_to_pay, name='go_to_pay'),
    path('ecpay_callback/', views.ecpay_callback, name='ecpay_callback'),
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('kitchen/complete/<int:order_id>/', views.complete_order, name='complete_order'),
    path('ecpay_return/', views.ecpay_return, name='ecpay_return'),
    path('brand_story/',views.brand_story,name='brand_story'),
    path('contact_us/',views.contact_us,name='contact_us'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('book_table/',views.book_table,name='book_table'),
    path('my_bookings/', views.my_bookings, name='my_bookings'),
    path('cancel_booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)