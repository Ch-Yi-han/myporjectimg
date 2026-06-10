
from django.db import models
from django.dispatch import receiver
from django.contrib.auth import get_user_model

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

class CustomMember(models.Model):
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

    def __str__(self):
        return self.username

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

class OrderItem(models.Model):
    order =models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items',verbose_name='訂單')
    item_name=models.CharField(max_length=100,verbose_name="餐點名稱(快照)")
    price = models.IntegerField(verbose_name="購買時價格")
    quantity = models.PositiveIntegerField(verbose_name="數量")