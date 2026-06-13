from django.contrib import admin

# Register your models here.
from .models import Dish  # 匯入你的菜單模型

# 💡 告訴 Django：我要在後台管理這個模型！
admin.site.register(Dish)
