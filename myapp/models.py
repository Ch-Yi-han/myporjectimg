from django.db import models

# Create your models here.
class Dish(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    # 💡 新手最推這行，會自動生成檔案路徑
    image = models.ImageField(upload_to='dishes/', default='dishes/default.jpg')
    description = models.TextField(blank=True, null=True, verbose_name="介紹")