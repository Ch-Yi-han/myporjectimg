from .models import Dish,CustomMember
from django.shortcuts import render, redirect
from .forms import CustomRegisterForm

from django.contrib.auth.hashers import check_password, make_password

def index(request):
    member_name = request.session.get('member_name')
    
    context = {
        'is_login': member_name is not None,
        'member_name': member_name # 把姓名傳給前端 HTML
    }
    return render(request, 'index.html', context)

def menu(request):
    member_name = request.session.get('member_name')
    dishes_data=Dish.objects.all()
    context ={
        'is_login': member_name is not None,
        'member_name': member_name,
        'dishes': dishes_data
    }
    return render(request,'menu.html',context)
def user_login(request):
    return render(request,'user_login.html')


def register(request):
    if request.method == 'POST':
        form=CustomRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user_login')
    else:
        form=CustomRegisterForm()

    return render(request,'register.html',{'form':form})

def user_login(request):
    error_message = None
    if request.method == 'POST':
        user_input_name=request.POST.get('username')
        user_input_pwd= request.POST.get('password')
        try:
                # 去我們自創的表撈人
                member = CustomMember.objects.get(username=user_input_name)
                
                # 👮‍♂️ 比對輸入的密碼跟資料庫的加密密碼合不合
                if check_password(user_input_pwd, member.password):
                    # 🎫 密碼正確！手動在瀏覽器 Session 寫入會員憑證
                    request.session['member_id'] = member.id
                    full_name = f"{member.last_name}{member.first_name}"
                    request.session['member_name'] = full_name
                    return redirect('index') # 前往首頁
                else:
                    error_message = "密碼錯誤或帳號錯誤！"
        except CustomMember.DoesNotExist:
                error_message = "帳號不存在！"

    return render(request, 'user_login.html', {'error_message': error_message})
def logout(request):
    # 💥 直接把瀏覽器 Session 裡的會員憑證撕毀清空
    if 'member_id' in request.session:
        del request.session['member_id']
    if 'member_name' in request.session:
        del request.session['member_name']
        
    print("👋 會員已安全登出")
    return redirect('index')