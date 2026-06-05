from django.db import models
from django.contrib .auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
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