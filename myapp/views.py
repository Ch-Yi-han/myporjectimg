from django.shortcuts import render, redirect,get_object_or_404
from .forms import CustomRegisterForm,UpdateProfileAndConfirmForm,ReservationForm
from django.contrib.auth import authenticate, login,logout  as django_logout
from django.contrib import messages
import random
from django.core.mail import send_mail
from .models import CustomMember,Dish,CartItem,Order,OrderItem,Reservation
from django.utils import timezone
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse,JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.timezone import localtime
# 引入綠界 SDK 相關套件（此處為示範邏輯）

from ecpay_payment_sdk import ECPayPaymentSdk
from django.shortcuts import get_object_or_404, redirect

# 首頁：讀取 session 裡的會員名稱，判斷使用者是否已登入，並把登入狀態傳給首頁模板。
def index(request):
    member_name = request.session.get('member_name')
    
    context = {
        'is_login': member_name is not None,
        'member_name': member_name # 把姓名傳給前端 HTML
    }
    return render(request, 'index.html', context)

# 菜單頁：從資料庫撈出所有 Dish 餐點資料，並把餐點清單與登入資訊傳到 menu.html。
def menu(request):
    member_name = request.session.get('member_name')
    dishes_data=Dish.objects.all()
    context ={
        'is_login': member_name is not None,
        'member_name': member_name,
        'dishes': dishes_data
    }
    return render(request,'menu.html',context)

# 登入頁面：單純顯示登入表單頁面；下方同名函式會覆蓋此函式，實際執行以後面的 user_login 為主。
def user_login(request):
    return render(request,'user_login.html')


# 註冊功能：處理會員註冊表單，驗證成功後會將密碼加密、儲存會員，並自動登入後回首頁。
def register(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            # # 1. 拿到資料物件
            user = form.save(commit=False)
            
            # # 2. 密碼雜湊加密
            user.set_password(form.cleaned_data['password'])
            
            # # 3. 正式寫入資料庫
            user.save()
            
            # 🎫 🌟【新加的大招】：註冊成功後，不用逼他去登入頁了，直接強行幫他辦理登入！
            login(request, user)
            
            # 🚀 直接高高興興地彈回首頁（此時已經是 100% 合法顧客登入狀態）
            return redirect('index')
    else:
        form = CustomRegisterForm()
        
    # 🌟 靈魂補救：就是漏了這行！確保 GET 請求進來時，會乖乖把註冊網頁畫出來！
    return render(request, 'register.html', {'form': form})

# 登入功能：接收帳號密碼，透過 Django authenticate 驗證，成功後建立登入狀態並導回首頁。
def user_login(request):
    error_message = None
    if request.method == 'POST':
        user_input_name = request.POST.get('username')
        user_input_pwd = request.POST.get('password')
        
        # 👮‍♂️ 1. 改用官方認證守門員：自動比對帳號、自動用 check_password 比對加密密碼
        user = authenticate(request, username=user_input_name, password=user_input_pwd)
        
        if user is not None:
            # 🎫 2. 核心關鍵：調用官方登入功能，這行會同時幫你處理好所有的 Session 和 request.user 綁定！
            login(request, user)
            
            # 3. 順利登入！轉跳到首頁或你想去的地方
            return redirect('index') 
        else:
            # 帳號不存在或密碼錯誤，authenticate 都會回傳 None
            error_message = "帳號或密碼錯誤！"

    return render(request, 'user_login.html', {'error_message': error_message})



# 登出功能：呼叫 Django 官方登出機制，並清除舊版手動 session 資料，最後回到首頁。
def logout(request):
    # 🎫 呼叫官方登出：這行會一槍斃命，直接把 request.user 的官方登入狀態徹底註銷！
    django_logout(request)
    
    # 🩹 安全補刀：順便把你以前手寫、可能殘留的舊 session 貼紙也清乾淨
    if 'member_id' in request.session:
        del request.session['member_id']
    if 'member_name' in request.session:
        del request.session['member_name']
        
    messages.success(request, '您已成功登出！')
    
    # 轉跳回首頁
    return redirect('index')

# 編輯會員資料：限制登入者使用，讓會員更新個人資料，若修改密碼會重新加密並維持登入狀態。
@login_required(login_url='/user_login/') # 🌟 1. 超級大招！沒登入直接踢去登入頁，不用自己寫 if if 了！
def edit_profile(request):
    # 🌟 2. 核心關鍵：因為是官方認證，當前登入的會員物件直接就躺在 request.user 裡面！
    member = request.user 

    if request.method == 'POST':
        form = UpdateProfileAndConfirmForm(request.POST, instance=member)
        if form.is_valid():
            # 🌟 3. 補刀安全防呆：如果你這個表單裡面有欄位是可以修改「密碼」的
            # 我們要用 set_password 確保密碼在寫入時有被再次狠狠加密！
            user = form.save(commit=False)
            if 'password' in form.cleaned_data and form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            
            user.save()
            
            # 🌟 4. 如果使用者改了密碼，官方的 Session 憑證會失效被踢出，這行能幫他自動更新憑證不被踢走！
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            messages.success(request, '個人資料已成功更新！')
            return redirect('edit_profile')
    else:
        form = UpdateProfileAndConfirmForm(instance=member)

    return render(request, 'edit_profile.html', {'form': form})
    

# 忘記密碼第一步：確認帳號與 Email 是否存在，若正確就產生 6 位數驗證碼並寄到信箱。
def forgot_password_request(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')

        try:
            user = CustomMember.objects.get(username=username, email=email)
            code = str(random.randint(100000, 999999))

            request.session['reset_code'] = code
            request.session['reset_user_id'] = user.id
            request.session.set_expiry(300)

            # 🟢 優化後的發信內容
            send_mail(
                '【聚福樓】您的密碼重設驗證碼 🔐', # 🌟 改成聚福樓，辨識度更高
                f'親愛的會員您好：\n\n您的密碼重設驗證碼為：【 {code} 】\n\n此驗證碼將於 5 分鐘後過期，請儘速回到網頁輸入完成驗證。\n\n聚福樓團隊 敬上',
                settings.EMAIL_HOST_USER, # 🌟 這裡改成自動抓取你 settings.py 設定好的官方帳號，最安全
                [email],
                fail_silently=False
            )

            messages.success(request, "驗證碼已發送到您的信箱，請至信箱查收！")
            return redirect('verify_code')

        except CustomMember.DoesNotExist:
            messages.error(request, "帳號或是電子信箱不正確，請重新確認。")
            
    return render(request, 'forgot_password_request.html')

# 忘記密碼第二步：比對使用者輸入的驗證碼與 session 中保存的驗證碼是否相同。
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
            return redirect('verify_code')
        
    
    return render(request,'verify_code.html')

# 忘記密碼第三步：驗證通過後讓使用者輸入新密碼，確認兩次密碼一致後更新會員密碼。
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
        user.set_password(password) 
        user.save()

        request.session.flush()
        messages.success(request,"密碼修改成功")
        return redirect('user_login')
    return render(request, 'reset_password.html')

# 取得目前會員：從舊版 session 的 member_id 查詢會員物件，找不到或未登入時回傳 None。
def get_current_member(request):
    member_id= request.session.get('member_id')
    if not member_id:
        return None
    try:
        return CustomMember.objects.get(id=member_id)
    except CustomMember.DoesNotExist:
        return None



# 線上點餐頁：顯示所有餐點，並依照目前登入者資料顯示會員名稱與登入狀態。
def order_online(request):
    member_name = None
    
    # 🟢 新寫法：直接用官方機制判斷有沒有登入
    if request.user.is_authenticated:
        member = request.user
        # 撈取姓名邏輯維持你的貼心防呆
        if member.last_name or member.first_name:
            member_name = f"{member.last_name}{member.first_name}"
        else:
            member_name = member.username 

    # 確保這行有撈到菜單
    dishes = Dish.objects.all() 

    # 打包送往前端
    return render(request, 'order_online.html', {
        'dishes': dishes,
        'member_name': member_name,
        'is_login': request.user.is_authenticated  # 🌟 直接用官方狀態，最準確！
    })
# ========1. 加入購物車 ===========

# 加入購物車：接收 AJAX POST 的餐點 id 與數量，建立或累加購物車項目，最後回傳 JSON 給前端。
def add_to_cart(request):
    # 🌟 1. 前端第一關防禦：如果是 AJAX 點擊，檢查有沒有官方登入
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error', 
            'message': '請先登入會員，才能開始點餐喔！'
        })

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        # 🟢 新寫法：直接拿最正確的當前官方登入者
        member = request.user 
        
        try:
            dish = Dish.objects.get(id=item_id)
            
            # 🛒 2. 尋找或建立購物車項目：把 member_id=member_id 改成跟你的 Model 一致
            # ⚠️ 註：如果你的 CartItem 欄位叫 user，請寫 user=member
            cart_item, created = CartItem.objects.get_or_create(
                member=member, 
                item=dish,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
                
            # 🧮 計算目前該會員購物車的總品項數量（用來更新右上角小紅點）
            # ⚠️ 註：同樣要對齊外鍵欄位名稱（member 或 user）
            cart_count = CartItem.objects.filter(member=member).count()
            
            # 🌟 3. 成功加入！必須老老實實回傳 JSON 格式，前端的 SweetAlert2 才會醒過來！
            return JsonResponse({
                'status': 'success', 
                'cart_count': cart_count
            })
            
        except Dish.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '找不到該項餐點'})
            
    return JsonResponse({'status': 'error', 'message': '無效的請求方式'})

#=========2.查看購物車============

# 查看購物車：列出目前登入會員的購物車內容，計算每項小計、總金額，並產生可選取餐時間。
@login_required(login_url='/user_login/') # 🛡️ 官方防禦：沒登入直接踢去登入頁！
def view_cart(request):
    # 🟢 新寫法：直接拿最乾淨的當前登入者
    member = request.user
    
    if member.last_name or member.first_name:
        member_name = f"{member.last_name}{member.first_name}"
    else:
        member_name = member.username

    # 🛒 撈出購物車項目：把 member_id=member_id 改成 member=member（對齊你的外鍵欄位名稱）
    # ⚠️ 註：如果你的 CartItem 模型裡欄位名稱真的叫 member_id，請改成 member_id=member.id
    cart_items = CartItem.objects.filter(member=member) 
    
    # 現場計算總金額
    for item in cart_items:
        item.subtotal = item.item.price * item.quantity
    total_amount = sum(cart_item.item.price * cart_item.quantity for cart_item in cart_items)
    
    # ⏰ 時間選單生成邏輯（維持原樣）
    START_HOUR = 11
    END_HOUR = 21
    TIME_INTERVAL = 15
    
    time_choices = []
    for hour in range(START_HOUR, END_HOUR + 1):
        for minute in range(0, 60, TIME_INTERVAL):
            if hour == END_HOUR and minute > 0:
                continue
            time_str = f"{hour:02d}:{minute:02d}"
            time_choices.append(time_str)

    # 🌟【大修復】：把原本分開宣告、會互相覆蓋的 context 融合成完整的一包！
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'member_name': member_name,
        'is_login': True, # 既然過了大門，絕對是登入狀態
        'time_choices': time_choices, # 時間清單也順利塞進來了！
    }
    
    return render(request, 'view_cart.html', context)

# 更新購物車數量：根據 increase/decrease 操作調整餐點數量，若數量歸零就刪除該項目。
@login_required(login_url='/user_login/')
def update_cart_quantity(request, item_id, action):
    member = request.user
    cart_item = get_object_or_404(CartItem, member=member, item_id=item_id)
    
    if action == 'increase':
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'decrease':
        cart_item.quantity -= 1
        if cart_item.quantity <= 0:
            cart_item.delete()
            # 🌟 如果商品被刪除了，回傳 deleted 狀態給前端
            return JsonResponse({'status': 'deleted', 'item_id': item_id})
        else:
            cart_item.save()
            
    # 計算該單項的新小計與整個購物車的新總金額
    subtotal = cart_item.item.price * cart_item.quantity
    
    # 重新計算總金額
    cart_items = CartItem.objects.filter(member=member)
    total_amount = sum(item.item.price * item.quantity for item in cart_items)
    
    # 🌟 核心改動：改回傳 JSON，不重新整理網頁
    return JsonResponse({
        'status': 'success',
        'quantity': cart_item.quantity,
        'subtotal': subtotal,
        'total_amount': total_amount
    })

#=======3.建立訂單(結帳) =========

# 結帳建立訂單：把購物車內容轉成 Order 與 OrderItem，儲存取餐時間後清空購物車。
@login_required(login_url='/user_login/')
def checkout(request):
    member=request.user
    
    cart_items = CartItem.objects.filter(member=member)
    if not cart_items.exists():
        return redirect('view_cart')
    
    if request.method == 'POST':
        pickup_date_str = request.POST.get('pickup_date')         # 例如 "2026-06-16"
        pickup_time_slot = request.POST.get('pickup_time_slot')   # 例如 "18:30"
        
        pickup_datetime = timezone.now()
        total_amount = sum(item.item.price * item.quantity for item in cart_items)
        
        # 🎯 組合標準字串，直接把日期和時間槽串在一起
        if pickup_date_str and pickup_time_slot:
            combined_str = f"{pickup_date_str} {pickup_time_slot}" # 完美得到 "2026-06-16 18:30"
            naive_datetime = datetime.strptime(combined_str, "%Y-%m-%d %H:%M")
            pickup_datetime = timezone.make_aware(naive_datetime)

        order = Order.objects.create(
            member=member,
            total_amount=total_amount,
            status='pending', # 或是你原本設定的狀態欄位
            pickup_time=pickup_datetime # 🌟 核心修正：把現在時間塞進去！
        )
        for item in cart_items:
            OrderItem.objects.create(  # 🌟 改成你的訂單明細/項目模型！
            order=order,            # 連接剛剛建立好的那筆主訂單
            item_name=item.item.name,
            price=item.item.price,
            quantity=item.quantity
        )
        cart_items.delete()

        return redirect('order_history')
    
    return redirect('view_cart')

# 訂單紀錄：列出目前登入會員的所有訂單，依建立時間由新到舊排序。
@login_required(login_url='/user_login/') # 🛡️ 官方防禦：沒登入直接踢走，登入了就絕對放行！
def order_history(request):
    # 🟢 新寫法：直接手拿官方最正確的當前登入者物件
    member = request.user
    
    # 🔍 撈出該會員的訂單：請把原本的 member_id=member_id 改成對齊你的外鍵名稱
    # ⚠️ 註：如果你的 Order 模型中連接會員的欄位叫做 user，請寫 user=member
    orders = Order.objects.filter(member=member).order_by('-created_at')
    
    # 打印一下看看有沒有順利拿到訂單數量
    print(f"=== [歷史訂單偵錯] 成功幫 {member.username} 撈到 {orders.count()} 筆訂單！ ===")

    # 🌟 完美的打包送去前端 HTML
    return render(request, 'order_history.html', {'orders': orders})

# 刪除訂單：只允許會員刪除自己的未付款訂單，已付款或製作中的訂單不能取消。
@login_required(login_url='/user_login/') # 🛡️ 官方防禦：確保刪除訂單時，百分之百是登入狀態！
def delete_order(request, order_id):
    # 🟢 新寫法：直接從 request.user 拿到當前登入的官方會員物件
    member = request.user
    
    # 🔍 抓出這筆訂單（請注意：把原本的 member_id=member_id 改成對齊你的外鍵欄位名稱）
    # ⚠️ 註：如果你的 Order 模型中連接會員的欄位叫做 user，請寫 user=member
    order = get_object_or_404(Order, id=order_id, member=member)
    
    # 🛡️ 安全防禦 2：只有「未付款」才能刪除！如果已經付款，不給刪！
    if order.status == '未付款' or order.status == 'pending':
        # 💥 瀟灑刪除訂單！（Django Cascade 機制會自動連帶把明細 OrderItem 一起刪乾淨）
        order.delete()
        messages.success(request, "訂單已成功取消並刪除！")
    else:
        messages.error(request, "該訂單已進入製作或已付款，無法取消！")
        
    # 🔄 刪除完畢後，流暢地回到已經改好、暢行無阻的歷史訂單頁面
    return redirect('order_history')

# 前往付款：建立綠界付款參數，產生自動送出的付款表單，將使用者導向綠界付款頁。
@login_required(login_url='/user_login/') # 🛡️ 官方防禦：確保付款時百分之百是登入狀態
def go_to_pay(request, order_id):
    # 🟢 新寫法：直接從 request.user 拿到當前官方登入會員
    member = request.user
    
    # 🔍 抓出這筆訂單（同時確保這筆訂單真的是屬於當前登入會員的）
    # ⚠️ 註：如果你的 Order 模型中連接會員的欄位叫做 user，請將下面的 member=member 改為 user=member
    order = get_object_or_404(Order, id=order_id, member=member)
    
    # 1. 🎯 使用綠界官方正牌的 V5 測試環境特店三件套初始化！
    ecpay_payment_sdk = ECPayPaymentSdk(
        MerchantID='3002607',
        HashKey='pwFHCqoQZGmho4w6',
        HashIV='EkRm7iFT261dpevs'
    )
    
    YOUR_DOMAIN = "http://192.168.59.2:8080" 
    
    # 2. 抓取同一個時間物件，確保訂單號和欄位時間絕對同步
    current_time = datetime.now()
    trade_no = current_time.strftime("JFL%Y%m%d%H%M%S")
    trade_date = current_time.strftime('%Y/%m/%d %H:%M:%S')
    
    # 3. 準備參數給官方 SDK
    # 注意：將產生的綠界訂單編號存入訂單資料庫中，方便後續對帳（Webhook callback 回來時使用）
    order.merchant_trade_no = trade_no
    order.save() 
    
    client_parameters = {
        'MerchantTradeNo': trade_no, 
        'MerchantTradeDate': trade_date,
        'PaymentType': 'aio',
        'TotalAmount': int(order.total_amount), 
        'TradeDesc': 'JufuLouShopOrderDescription',
        'ItemName': 'JufuLouDeliciousMeal',
        'ReturnURL': f'{YOUR_DOMAIN}/ecpay_callback/', 
        'ChoosePayment': 'Credit', 
        'EncryptType': 1, # 1 代表用 SHA256 加密
        'OrderResultURL': f'{YOUR_DOMAIN}/ecpay_return/',
    }
    
    try:
        # 4. ⭕ 讓官方 SDK 自己去跑內部邏輯與 CheckMacValue 計算！
        final_params = ecpay_payment_sdk.create_order(client_parameters)
        
        action_url = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'
        
        # 5. 讓 SDK 噴出自動提交的 HTML 表單並直接渲染出去
        html_form = ecpay_payment_sdk.gen_html_post_form(action_url, final_params)
        return HttpResponse(html_form)
        
    except Exception as e:
        return HttpResponse(f'建立綠界訂單失敗: {e}')

# 綠界付款通知：綠界伺服器背景呼叫此網址，確認付款成功後更新訂單狀態並回傳 1|OK。
@csrf_exempt # 🚨 綠界是從外部發 POST 過來，必須關閉 CSRF 保護，否則會被 Django 擋掉！
def ecpay_callback(request):
    if request.method == 'POST':
        # 綠界會把所有交易結果塞在 request.POST 裡面
        ecpay_data = request.POST.dict()
        
        # 🟢 綠界官方規範：當 RtnCode == '1' 時，代表消費者真的付款成功了！
        rtn_code = ecpay_data.get('RtnCode')
        merchant_trade_no = ecpay_data.get('MerchantTradeNo') # 例如 JFL20260613XXXX
        
        if rtn_code == '1':
            try:
                # 1. 解析出我們當初在訂單編號裡埋的真實資料庫 Order ID
                # 我們當初的格式是：f"JFL{order.id}x{時間戳記}" 或者時間流水號
                # 如果你是用時間流水號，通常會在建立訂單時，把這個 trade_no 存進資料庫的某個欄位（例如 status_code 或備用欄位）
                # 這裡假設你的 Order Model 有一個欄位叫 `merchant_trade_no` 用來記錄這次發給綠界的單號：
                order = Order.objects.get(merchant_trade_no=merchant_trade_no)
                
                # 2. 🟢 成功付款！將狀態改為「準備中」
                order.status = 'preparing' 
                order.is_paid = True # 標記已付款
                order.save()
                
                # 3. 告訴綠界：我們收到囉！不准再發重試訊號過來（這行是綠界官方規定的標準回應）
                return HttpResponse('1|OK')
            except Order.DoesNotExist:
                return HttpResponse('0|Order NotFound')

    return HttpResponse('0|Fail')

# 綠界付款結果頁：付款完成後由綠界導回網站，更新訂單付款狀態並寄出付款成功通知信。
@csrf_exempt # 🛡️ 綠界從外部 POST 回來，一定要加這行免除 CSRF 檢查
def ecpay_return(request):
    if request.method == 'POST':
        ecpay_data = request.POST.dict()
        rtn_code = ecpay_data.get('RtnCode')
        merchant_trade_no = ecpay_data.get('MerchantTradeNo')
        
        if rtn_code == '1': 
            try:
                order = Order.objects.get(merchant_trade_no=merchant_trade_no)
                
                # 🛡️ 安全防禦：如果 status 已經是 'paid'，代表已經處理過，不要重複寄信
                if order.status != 'paid':
                    # 1. 更新訂單狀態與付款標記
                    order.status = 'paid'
                    order.is_paid = True
                    order.save()
                    
                    # 2. 🚀 線上點餐付款成功寄信邏輯
                    subject = f'【聚福樓】線上點餐付款成功通知（訂單編號：{order.id}）'
                    tw_time = localtime(order.pickup_time).strftime("%Y-%m-%d %H:%M")
                    # 這裡利用 \n 做換行，讓客人收信時排版乾淨整齊
                    message = (
                        f'親愛的聚福樓會員您好：\n\n'
                        f'我們已成功收到您的線上點餐款項！\n'
                        f'===============================\n'
                        f' 訂單編號：{order.id}\n'
                        f' 付款金額：NT$ {int(order.total_amount)} 元\n'
                        f' 預約取餐時間：{tw_time}\n'
                        f'===============================\n\n'
                        f'廚房已經收到您的訂單並開始全力製作，期待您的蒞臨取餐！'
                    )
                    
                    # 取得當前會員的 Email (對應你的 member 欄位)
                    user_email = order.member.email 
                    
                    # 執行寄信
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user_email],
                        fail_silently=True # 設為 True，確保萬一郵件伺服器連不上，也不會讓網頁死當
                    )
                    
            except Order.DoesNotExist:
                pass
                
    # 🎯 處理完綠界資料後，順利把顧客導向歷史紀錄頁面
    return redirect('order_history')

# 廚房後台：列出已付款待製作訂單，以及最近完成的訂單，提供廚房查看出餐狀態。
def kitchen_dashboard(request):
    # 換回最原始、可執行的 items
    preparing_orders = Order.objects.filter(status='paid').prefetch_related('items').order_by('created_at')
    completed_orders = Order.objects.filter(status='completed').prefetch_related('items').order_by('-id')[:10]
    
    context = {
        'preparing_orders': preparing_orders,
        'completed_orders': completed_orders,
    }
    return render(request, 'kitchen_dashboard.html', context)
# 🟢 點擊按鈕切換狀態的動作

# 完成訂單：廚房點擊完成後，將已付款訂單狀態改成 completed，並回到廚房後台。
def complete_order(request, order_id):
    # 找到訂單，並把狀態從「準備中」改成「準備完成」
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'paid':
        order.status = 'completed'
        order.save()
    return redirect('kitchen_dashboard')
    
# 建立訂單時間檢查：示範檢查取餐時間是否在營業時間內，目前只處理超出時間的錯誤導回。
def create_order(request):
    if request.method == "POST":
        pickup_hour_str = request.POST.get('pickup_hour') # 例如 "10:24"
        
        if pickup_hour_str:
            hour = int(pickup_hour_str.split(':')[0])
            # 🎯 檢查：如果小於 11 點或大於 21 點
            if hour < 11 or hour > 21:
                messages.error(request, "超出營業時間，取餐時間請選擇 11:00 ~ 21:00 之間！")
                return redirect('order_cart_page')

# 品牌故事頁：顯示餐廳品牌故事靜態頁面。
def brand_story(request):
    return render(request,'brand_story.html')

# 聯絡我們頁：顯示餐廳聯絡資訊靜態頁面。
def contact_us (request):
    return render(request,'contact_us.html')


# 線上訂位：顯示訂位表單，送出後建立 Reservation，並寄送訂位成功通知信。
@login_required(login_url='/user_login/')
def book_table(request):
    user_full_name = f"{request.user.last_name}{request.user.first_name}"
    
    if request.method == 'POST':
        # 🌟 直接用原本的 request.POST，不搞複製了
        form = ReservationForm(request.POST)
        
        if form.is_valid():
            # 🌟 關鍵核心：先 commit=False 拿到訂位物件，這時資料庫還沒寫入
            reservation = form.save(commit=False)
            
            # 🌟 在這裡，親手把目前登入的官方會員 request.user 狠狠塞給它！
            reservation.user = request.user
            
            # 正式寫入資料庫！
            reservation.save()
            
            # 🚀 【在這裡加入線上訂位成功的寄信邏輯】
            try:
                subject = f'【聚福樓】您的中式料理訂位已確認（訂位編號：{reservation.id}）'
                
                # 這裡假設你的 ReservationForm / Model 欄位有名稱、日期、時間、人數
                # 請根據你 Reservation 實際的欄位名稱調整（例如 reservation.date, reservation.num_people 等）
                message = (
                    f'親愛的 {user_full_name} 貴賓您好：\n\n'
                    f'感謝您選擇聚福樓！我們已為您保留座位，期待您的光臨。\n'
                    f'===============================\n'
                    f' 訂位編號：{reservation.id}\n'
                    f' 訂位姓名：{user_full_name} 貴賓\n'
                    f' 訂位日期：{reservation.date}\n'  # ⚠️ 欄位名請依 Model 實際狀況修改
                    f' 訂位時間：{reservation.time_slot}\n'  # ⚠️ 欄位名請依 Model 實際狀況修改
                    f' 訂位人數：{reservation.guests} 位\n'  # ⚠️ 欄位名請依 Model 實際狀況修改
                    f'===============================\n\n'
                    f'※ 溫馨提醒：若需取消或變更訂位，請提前來電告知。謝謝您！'
                )
                
                # 收件人直接抓目前登入使用者的 Email
                user_email = request.user.email
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_email],
                    fail_silently=True # 設為 True，確保郵件伺服器如果有萬一，客人的網頁也不會死當
                )
            except Exception as e:
                # 這裡可以用 print 或 logging 紀錄，不影響使用者
                print(f"訂位成功信件發送失敗: {e}")
            
            messages.success(request, '訂位成功！')
            return redirect('book_table')
        else:
            print(form.errors) # 防呆印出
            
    else:
        initial_data = {
            'name': user_full_name,
            'phone': getattr(request.user, 'phone', ''),
            'email': request.user.email,
        }
        form = ReservationForm(initial=initial_data)

    return render(request, 'book_table.html', {'form': form})

# 我的訂位：查詢目前登入會員的所有訂位紀錄，依訂位日期由新到舊排序。
@login_required(login_url='/user_login/')
def my_bookings(request):
    # 🟢 修正：把 filter(member=...) 改成 filter(user=...) 來對齊你的模型欄位
    bookings = Reservation.objects.filter(user=request.user).order_by('-date')
    return render(request, 'my_bookings.html', {'bookings': bookings})


# 取消訂位：確認該訂位屬於目前登入會員後刪除，並回到我的訂位頁。
@login_required(login_url='/user_login/')
def cancel_booking(request, booking_id):
    # 🟢 修正：把 get_object_or_404 裡面的 member=... 改成 user=... 
    booking = get_object_or_404(Reservation, id=booking_id, user=request.user)
    
    # 💥 取消訂位
    booking.delete()
    messages.success(request, "您的訂位已成功取消！")
    return redirect('my_bookings')
