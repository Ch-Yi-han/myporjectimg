from django.shortcuts import render
from .models import Dish
from django.shortcuts import render, redirect
from .forms import RegisterForm
from django.shortcuts import render, redirect


def home(request):
    return render(request,'home.html')

def menu(request):
    dishes_data=Dish.objects.all()
    context ={
        'dishes': dishes_data
    }
    return render(request,'menu.html',context)
def user_login(request):
    return render(request,'user_login.html')

def register(request):
    if request.method == 'POST':
        form=RegisterForm(request.Post)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form=RegisterForm
    return render(request,'register.html')

