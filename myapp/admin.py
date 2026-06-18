from django.contrib import admin
from .models import CustomMember, Reservation 
from itertools import groupby
from operator import attrgetter
# Register your models here.
from .models import Dish  # 匯入你的菜單模型

# 💡 告訴 Django：我要在後台管理這個模型！
admin.site.register(Dish)


# 註冊會員模型（你原本應該就有了）
admin.site.register(CustomMember)

# 🌟 關鍵：加上這行，把訂位系統註冊到後台！
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'date', 'time_slot', 'guests', 'is_arrived')
    list_editable = ['is_arrived']
    list_filter = ('date', 'time_slot', 'is_arrived')
    search_fields = ('name', 'phone')
    
    # 🌟 核心魔法：指定這個模型後台列表，改用我們自訂的客製化摺疊 HTML 範本！
    change_list_template = "admin/reservation_accordion_list.html"

    # 2. 覆寫 Django 丟資料給後台畫面的大腦
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # 🟢 A. 唯獨撈出「今天到未來」的訂位，並且嚴格按照日期排序（groupby 前必須先排序）
        from django.utils import timezone
        today = timezone.localdate()
        
        # 如果管理員有使用右側篩選或上方搜尋，由 Django 原生處理；
        # 這裡我們預設直接撈出今日及未來的全部訂位供摺疊展示
        queryset = self.get_queryset(request).filter(date__gte=today).order_by('date', 'time_slot')
        
        # 🟢 B. 發動 Python 分組大絕：按「日期(date)」將訂位資料打包
        grouped_bookings = []
        for date, items in groupby(queryset, key=attrgetter('date')):
            item_list = list(items)
            grouped_bookings.append({
                'date': date,
                'count': len(item_list), # 這一天的總筆數
                'bookings': item_list    # 這一天的所有訂位明細資料
            })
            
        # 🟢 C. 把打包好的巧克力袋子丟給前端 HTML
        extra_context['grouped_bookings'] = grouped_bookings
        
        return super().changelist_view(request, extra_context=extra_context)