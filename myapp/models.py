from django.db import models

# Create your models here.
class Dish(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    # 💡 新手最推這行，會自動生成檔案路徑
    image = models.ImageField(upload_to='dishes/', default='dishes/default.jpg')
    spicy_level = models.IntegerField(default=0, verbose_name="辣度等級")
    description = models.TextField(blank=True, null=True, verbose_name="介紹")
    
    
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