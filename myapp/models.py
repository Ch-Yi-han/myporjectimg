
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,PermissionsMixin

# Create your models here.
class Dish(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    # 💡 新手最推這行，會自動生成檔案路徑
    image = models.ImageField(upload_to='dishes/', default='dishes/default.jpg')
    spicy_level = models.IntegerField(default=0, verbose_name="辣度等級")
    description = models.TextField(blank=True, null=True, verbose_name="介紹")
    
    is_recommended = models.BooleanField(default=False, verbose_name="主廚推薦")

    CATEGORY_CHOICES = [
        ('appetizer', '開胃菜'),
        ('meat', '肉類'),
        ('seafood', '海鮮'),
        ('vegetarian', '素食'),
        ('soup', '湯品'),
        ('dessert','甜點'),
        ('rice_and_noodles', '飯類和麵類'),
        ('egg_and_tofu', '蛋類和豆腐類'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='appetizer', verbose_name="分類")
    is_available = models.BooleanField(default=True, verbose_name="是否供應") # 點餐功能需要這個
    class Meta:
        verbose_name = "菜色"
        verbose_name_plural = "菜單管理"

    # 💡 修正 Dish object (1) 的顯示（必加！）
    def __str__(self):
        return self.name

    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='all',
        verbose_name="網頁分類標籤"
    )

class CustomMemberManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not username:
            raise ValueError('必須輸入使用者名稱')
        user = self.model(username=username, **extra_fields)
        if password:
            user.set_password(password) # 自動幫密碼雜湊加密
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser 必須設定 is_staff=True。')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser 必須設定 is_superuser=True。')

        # 最後再呼叫上面的顧客邏輯去幫管理者加密密碼並存檔
        return self.create_user(username, password, **extra_fields)
    
class CustomMember(AbstractBaseUser,PermissionsMixin):
    # 帳號設定為唯一值 (unique=True)，不允許重複
    username = models.CharField('會員帳號', max_length=50, unique=True)
    last_name = models.CharField('姓氏', max_length=20)
    first_name = models.CharField('名字', max_length=30)
    password = models.CharField('密碼', max_length=128)
    email = models.EmailField('電子信箱', unique=True)
    phone = models.CharField('電話號碼', max_length=15, blank=True, null=True)
    birthday = models.DateField('生日', blank=True, null=True)
    
    GENDER_CHOICES = [('M', '男'), ('F', '女'), ('O', '其他')]
    gender = models.CharField('性別', max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    
    created_at = models.DateTimeField('註冊時間', auto_now_add=True)

    is_active = models.BooleanField(default=True, verbose_name="啟用狀態")
    is_staff = models.BooleanField(default=False, verbose_name="後台登入權限")

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    objects = CustomMemberManager()

    def __str__(self):
        return self.username
    class Meta:
        db_table = 'myapp_custommember'
        app_label = 'myapp'
    
class Reservation(models.Model):
    # 關聯會員（做法 B）
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
     
        verbose_name="關聯會員",
        related_name="reservations"
    )

    # 客戶基本資料
    name = models.CharField(max_length=50, verbose_name="訂位人姓名")
    phone = models.CharField(max_length=15, verbose_name="聯絡電話")
    email = models.EmailField(verbose_name="電子信箱", blank=True, null=True)
    
    # 訂位詳細資訊
    date = models.DateField(verbose_name="訂位日期")
    
    # 🌟 這裡就是更動的地方：不需要 choices 也不需要關聯別的表，直接用 CharField 存時間字串
    time_slot = models.CharField(max_length=10, verbose_name="用餐時段")
    
    guests = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)], 
        verbose_name="用餐人數"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="備註")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="填單時間")
    is_arrived = models.BooleanField(default=False, verbose_name="客人是否已到店")

    class Meta:
        verbose_name = "線上訂位"
        verbose_name_plural = "線上訂位管理"
        ordering = ['-date', 'time_slot']

    def __str__(self):
        return f"{self.date} {self.time_slot} - {self.name} ({self.guests}人)"

    # 檢查剩餘座位邏輯（維持不變，依然可用）
    @staticmethod
    def get_available_seats(date, time_slot):
        MAX_SEATS = 50  # 餐廳每時段上限人數
        booked_guests = Reservation.objects.filter(
            date=date, 
            time_slot=time_slot
        ).aggregate(total=models.Sum('guests'))['total'] or 0
        return MAX_SEATS - booked_guests

class MenuItem(models.Model):
    name= models.CharField(max_length=100,verbose_name="餐點名稱")
    price = models.IntegerField(verbose_name="價格")
    is_available=models.BooleanField(default=True,verbose_name="是否供應")

    def __str__(self):
        return self.name

class CartItem(models.Model):
    member =models.ForeignKey(CustomMember,on_delete=models.CASCADE,verbose_name="會員")
    item = models.ForeignKey(Dish,on_delete=models.CASCADE,verbose_name="餐點")
    quantity=models.PositiveIntegerField(default=1,verbose_name="數量")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.item.price * self.quantity

class Order(models.Model):
    STATUS_CHOICES =[
        ('pending','未付款'),
        ('paid','已付款/準備中'),
        ('completed','已完成'),
        ('cancelled','已取消'),
    ]
    member = models.ForeignKey(CustomMember,on_delete=models.CASCADE,verbose_name="會員")
    total_amount= models.IntegerField(verbose_name="總金額")
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending',verbose_name='頂單狀態')
    created_at = models.DateTimeField(auto_created=True,verbose_name='訂單時間')
    merchant_trade_no = models.CharField(max_length=50,unique=True,blank=True,null=True)
    pickup_time = models.DateTimeField(blank=False, null=False, default=timezone.now,verbose_name="預約取餐時間")
    created_at = models.DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order =models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items',verbose_name='訂單')
    item_name=models.CharField(max_length=100,verbose_name="餐點名稱(快照)")
    price = models.IntegerField(verbose_name="購買時價格")
    quantity = models.PositiveIntegerField(verbose_name="數量")

