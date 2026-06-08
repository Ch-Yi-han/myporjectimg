from .models import Dish,CustomMember
from django.shortcuts import render, redirect
from .forms import CustomRegisterForm
from django.contrib.auth.hashers import check_password,make_password
from myapp.models import CustomMember
from django.contrib import messages
import random
from django.core.mail import send_mail

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

def forgot_password_request(request):
    if request.method == "POST":
        username=request.POST.get('username')
        email=request.POST.get('email')

        try:
            user=CustomMember.objects.get(username=username ,email=email)
            code=str(random.randint(100000,999999))

            request.session['reset_code'] = code
            request.session['reset_user_id'] = user.id
            request.session.set_expiry(300)

            send_mail(
                '【網站名稱】密碼重設驗證碼',
                f'您的驗證碼為：{code}，請於 5 分鐘內輸入。',
                'from@example.com',
                [email],
                fail_silently=False
            )

            messages.success(request,"驗證碼已發送到您的信箱!")
            return redirect('verify_code')

        except CustomMember.DoesNotExist:
            messages.error(request,"帳號或是電子信箱不正確")
    return render(request,'forgot_password_request.html')

def verify_code(request):
    if 'reset_code' not in request.session:
        messages.error(request,"驗證碼已失效，請重新申請")
        return redirect('forgot_password_request')
    
    if request.method == "POST":
        input_code =request.POST.get('code')
        session_code=request.session.get('reset_code')
        
        if input_code == session_code:
            request.session['code_verified']=True
            return redirect('reset_password')
        else:
            messages.error(request,"驗證碼錯誤，請重新輸入")
    
    return render(request,'verify_code.html')

def reset_password(request):
    if not request.session.get('code_verified'):
        messages.error(request,"請先完成驗證")
        return redirect('forgot_password_request')
    if request.method == "POST":
        password= request.POST.get('password')
        password_confirm =request.POST.get('password_confirm')

        if password !=password_confirm:
            messages.error(request,"兩次輸入的密碼不相同")
            return render(request,'reset_password.html')
        
        user_id = request.session.get('reset_user_id')
        user = CustomMember.objects.get(id=user_id)
        user.password = make_password(password)
        user.save()

        request.session.flush()
        messages.success(request,"密碼修改成功")
        return redirect('user_login')
    return render(request,'reset_password.html')