from django.contrib import admin
from .models import CustomMember, Reservation ,FinancialCategory, FinancialRecord
from itertools import groupby
from operator import attrgetter
from .models import Dish  # 匯入你的菜單模型
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
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

        # 一次彙總每個日期、時段的訂位人數，避免逐筆查詢資料庫。
        slot_totals = {
            (slot['date'], slot['time_slot']): slot['total_guests']
            for slot in queryset.values('date', 'time_slot').annotate(
                total_guests=Sum('guests')
            )
        }
        
        # 🟢 B. 發動 Python 分組大絕：按「日期(date)」將訂位資料打包
        grouped_bookings = []
        for date, items in groupby(queryset, key=attrgetter('date')):
            item_list = list(items)
            for booking in item_list:
                booked_guests = slot_totals[(booking.date, booking.time_slot)]
                booking.available_seats = max(
                    Reservation.MAX_SEATS_PER_SLOT - booked_guests,
                    0
                )
            grouped_bookings.append({
                'date': date,
                'count': len(item_list), # 這一天的總筆數
                'bookings': item_list    # 這一天的所有訂位明細資料
            })
            
        # 🟢 C. 把打包好的巧克力袋子丟給前端 HTML
        extra_context['grouped_bookings'] = grouped_bookings
        extra_context['max_seats_per_slot'] = Reservation.MAX_SEATS_PER_SLOT
        
        return super().changelist_view(request, extra_context=extra_context)

class RecordTypeTabsFilter(admin.SimpleListFilter):
    title = _('收支分類')
    parameter_name = 'record_type'

    def lookups(self, request, model_admin):
        return (
            ('INCOME', '只看收入 💰'),
            ('EXPENSE', '只看支出 💸'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'INCOME':
            return queryset.filter(category__record_type='INCOME')
        if self.value() == 'EXPENSE':
            return queryset.filter(category__record_type='EXPENSE')
        return queryset

@admin.register(FinancialCategory)
class FinancialCategoryAdmin(admin.ModelAdmin):
    list_display = ['record_type', 'name']
    list_filter = ['record_type']

@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = ['date', 'get_type_display', 'category', 'amount', 'note']
    list_display_links = ['date', 'category']
    
    # 💡 重點修改：把剛才建立的 RecordTypeTabsFilter 放進來（最前面）
    list_filter = [RecordTypeTabsFilter, 'date', 'category'] 
    
    date_hierarchy = 'date'
    search_fields = ['note', 'category__name', 'amount']

    # 讓流水帳列表能一眼看出是收入還是支出
    def get_type_display(self, obj):
        return obj.category.get_record_type_display()
    get_type_display.short_description = "收支大類"

    # 🚀 核心魔改：讓 Django 後台根據你篩選的時間與頁籤，自動計算總金額
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            if hasattr(response, 'context_data'):
                cl = response.context_data['cl']
                queryset = cl.get_queryset(request)
                
                total_income = queryset.filter(category__record_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
                total_expense = queryset.filter(category__record_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
                net_profit = total_income - total_expense
                
                extra_context = extra_context or {}
                extra_context['calculated_data'] = {
                    'total_income': total_income,
                    'total_expense': total_expense,
                    'net_profit': net_profit,
                }
                response.context_data.update(extra_context)
        except (AttributeError, KeyError):
            pass
            
        return response
