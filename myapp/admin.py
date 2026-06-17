from django.contrib import admin
from .models import CustomMember, Reservation 
# Register your models here.
from .models import Dish  # 匯入你的菜單模型

# 💡 告訴 Django：我要在後台管理這個模型！
admin.site.register(Dish)


# 註冊會員模型（你原本應該就有了）
admin.site.register(CustomMember)

# 🌟 關鍵：加上這行，把訂位系統註冊到後台！
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    # 讓後台表格一條一條顯示漂亮的欄位資訊
    list_display = ('name', 'phone', 'date', 'time_slot', 'guests')
    # 建立右側側邊欄，讓你可以快速篩選日期
    list_filter = ('date', 'time_slot')
    # 建立搜尋框，可以輸入客人名字或電話來找訂位
    search_fields = ('name', 'phone')