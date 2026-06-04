from django.shortcuts import render
from .models import Dish
from django.shortcuts import render, redirect
from .forms import RegisterForm
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm,forms

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

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="帳號",
        widget=forms.TextInput(attrs={
            'class': 'form-control', # 如果你有用 Bootstrap 樣式
            'placeholder': '請輸入帳號'
        })
    )
def register(request):
    if request.method == 'POST':
        form=RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user_login')
    else:
        form=CustomLoginForm()

    return render(request,'register.html',{'form':form})

