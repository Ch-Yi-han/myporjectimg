from django.shortcuts import render
from .models import Dish

def home(request):
    return render(request,'home.html')

def menu(request):
    dishes_data=Dish.objects.all()
    context ={
        'dishes': dishes_data
    }
    return render(request,'menu.html',context)