from django.shortcuts import render, redirect,get_object_or_404
from .forms import CustomRegisterForm,UpdateProfileAndConfirmForm,ReservationForm
from django.contrib.auth import authenticate, login,logout  as django_logout
from django.contrib import messages
import random
from django.core.mail import send_mail
from .models import CustomMember,Dish,CartItem,Order,OrderItem
from django.utils import timezone
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse,JsonResponse
from django.contrib.auth.decorators import login_required

# 引入綠界 SDK 相關套件（此處為示範邏輯）

from ecpay_payment_sdk import ECPayPaymentSdk
from django.shortcuts import get_object_or_404, redirect

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
            return redirect('verify_code')
        
    
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
    return render(request, 'reset_password.html')

def get_current_member(request):
    member_id= request.session.get('member_id')
    if not member_id:
        return None
    try:
        return CustomMember.objects.get(id=member_id)
    except CustomMember.DoesNotExist:
        return None



def order_online(request):
    member_id = request.session.get('member_id')
    member_name = None
    
    # 🚩 測試旗子 1：看看有沒有拿到 Session ID
    print(f"=== [測試] 當前點餐頁面的 member_id 是: {member_id} ===")
    
    if member_id:
        try:
            member = CustomMember.objects.get(id=member_id)
            if member.last_name or member.first_name:
                member_name = f"{member.last_name}{member.first_name}"
            else:
                member_name = member.username # 防呆：如果剛好沒填姓名，就拿帳號頂替
        except CustomMember.DoesNotExist:
            pass

    # 確保這行有撈到菜單
    dishes = Dish.objects.all() 

    # 🌟 用最乾淨的方式一口氣打包，絕對不重複宣告 context
    return render(request, 'order_online.html', {
        'dishes': dishes,
        'member_name': member_name,
        'is_login': True if member_name else False
    })
# ========1. 加入購物車 ===========
def add_to_cart(request):
    member = get_current_member(request)
    if not member:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': '請先登入會員再開始點餐喔！'})
        return redirect('login')

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity',1))
        item = get_object_or_404(Dish,id=item_id)
        #檢查購物車是否已有該有會員點餐的這項餐點
        cart_item,created=CartItem.objects.get_or_create(
            member=member,
            item= item,
            defaults={'quantity':quantity}
        )
        if not created:
            cart_item.quantity +=quantity
            cart_item.save()
        # 3. 🎯 核心修改：計算目前該會員購物車裡的「總餐點件數」
        # 這樣右上角的購物車數量圖示（如果有做的話）才能即時更新
        from django.db.models import Sum
        total_items = CartItem.objects.filter(member_id=member).aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # 4. 🎯 核心大絕：判斷如果是前端 JavaScript (AJAX) 發過來的請求
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': f'成功將 {item.name} 加入購物車！',
                'cart_count': total_items # 傳回最新總數量
            })
            
        # 保險：如果是不支援 JavaScript 的老舊瀏覽器，維持原本的整頁跳轉
        return redirect('order_online')

        return redirect('order_online')

#=========2.查看購物車============
def view_cart(request):
    # 🛡️ 核心未登入防禦：只要拿不到 session 裡的 member_id，立刻踢去登入
    member_id = request.session.get('member_id')
    if not member_id:
        return redirect('user_login')
    
    # 🔍 已登入，順利拿著 member_id 去撈 CustomMember 的 username
    member_name = None
    try:
        member = CustomMember.objects.get(id=member_id)
        if member.last_name or member.first_name:
            member_name = f"{member.last_name}{member.first_name}"
        else:
            member_name = member.username
    except CustomMember.DoesNotExist:
        pass

    # 🛒 撈出購物車項目並現場計算總金額
    cart_items = CartItem.objects.filter(member_id=member_id)
    for item in cart_items:
        item.subtotal = item.item.price * item.quantity
    total_amount = sum(cart_item.item.price * cart_item.quantity for cart_item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'member_name': member_name,
        'is_login': True if member_name else False
    }
    START_HOUR = 11
    END_HOUR = 21
    TIME_INTERVAL = 15
    
    time_choices = []
    for hour in range(START_HOUR, END_HOUR + 1):
        for minute in range(0, 60, TIME_INTERVAL):
            # 如果是最後一個小時（21 點），通常只需要 21:00 即可，後面的 21:15... 略過
            if hour == END_HOUR and minute > 0:
                continue
            time_str = f"{hour:02d}:{minute:02d}"
            time_choices.append(time_str)

    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'time_choices': time_choices, # 🔥 將合併好的名冊送往前端
    }
    return render(request, 'view_cart.html', context)

def update_cart_quantity(request, item_id, action):
    member_id = request.session.get('member_id')
    if not member_id:
        return redirect('user_login')
        
    # 🔍 抓出購物車裡對應的餐點項目
    cart_item = get_object_or_404(CartItem, member_id=member_id, item_id=item_id)
    
    if action == 'increase':
        # ➕ 按了加號，數量加 1
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'decrease':
        # ➖ 按了減號，數量減 1
        cart_item.quantity -= 1
        
        # 🌟【核心關鍵】：如果減完後數量變成 0（或小於0），直接從購物車徹底移除這道菜！
        if cart_item.quantity <= 0:
            cart_item.delete()
        else:
            cart_item.save()
            
    # 🔄 處理完畢後，流暢地重新整理購物車畫面
    return redirect('view_cart')

#=======3.建立訂單(結帳) =========
def checkout(request):
    member=get_current_member(request)
    
    if not member:
        return redirect('user_login')
    
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

def order_history(request):
    member_id = request.session.get('member_id')
    # 💡 預防 Session 掉線的防護罩：如果沒登入，先隨便導向一個測試用的預設會員(例如 1)，或是引導去登入
    if not member_id:
     
        return redirect('user_login')
        
    # 換回最原始、可執行的 items 預先載入
    orders = Order.objects.filter(member_id=member_id).prefetch_related('items').order_by('-id')
    return render(request, 'order_history.html', {'orders': orders})
def delete_order(request, order_id):
    # 🛡️ 安全防禦 1：沒登入不能亂刪
    member_id = request.session.get('member_id')
    if not member_id:
        return redirect('user_login')
        
    # 🔍 抓出這筆訂單（同時確保這筆訂單真的是這個會員的）
    order = get_object_or_404(Order, id=order_id, member_id=member_id)
    
    # 🛡️ 安全防禦 2：只有「未付款」才能刪除！如果已經付款，不給刪！
    # 💡 請對照你資料庫存未付款的字串，如果是 'pending' 或 '未付款'，請改成對應的字串
    if order.status == '未付款' or order.status == 'pending':
        # 💥 瀟灑刪除訂單！（Django 會自動連帶把跟這筆訂單綁在一起的 OrderItem 明細一起刪乾淨）
        order.delete()
        messages.success(request, "訂單已成功取消並刪除！")
    else:
        messages.error(request, "該訂單已進入製作或已付款，無法取消！")
        
    # 🔄 刪除完畢後，流暢地回到歷史訂單頁面
    return redirect('order_history')


def go_to_pay(request, order_id):
    member_id = request.session.get('member_id')
    if not member_id:
        return redirect('user_login')
        
    order = get_object_or_404(Order, id=order_id, member_id=member_id)
    
    # 1. 🎯 使用剛才截圖中，官方正牌的 V5 測試環境特店三件套初始化！
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
    
    # 3. 準備最純淨的參數給官方 SDK 大腦
    # 注意：TotalAmount 必須是 int（整數），因為 SDK 內部會進行型態檢查！
    order.merchant_trade_no = trade_no
    order.save() # 記得一定要 save() 存進資料庫！
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
        # 4. ⭕ 讓官方 SDK 自己去跑內部邏輯！
        # 它會自動補上 MerchantID，並且用它內建的完整公式算出 100% 正確的 CheckMacValue
        final_params = ecpay_payment_sdk.create_order(client_parameters)
        
        action_url = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'
        
        # 5. 讓 SDK 噴出自動提交的 HTML 表單
        html_form = ecpay_payment_sdk.gen_html_post_form(action_url, final_params)
        return HttpResponse(html_form)
        
    except Exception as e:
        return HttpResponse(f'建立訂單失敗: {e}')
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

@csrf_exempt
def ecpay_return(request):
    if request.method == 'POST':
        ecpay_data = request.POST.dict()
        rtn_code = ecpay_data.get('RtnCode')
        merchant_trade_no = ecpay_data.get('MerchantTradeNo')
        
        # 為了保險，這裡跳轉回來時我們再撈一次訂單改狀態，防止本機端背景收不到訊號
        if rtn_code == '1': 
            try:
                order = Order.objects.get(merchant_trade_no=merchant_trade_no)
                
                order.status = 'paid'
                order.is_paid = True        # 標記已付款
                order.save()
            except Order.DoesNotExist:
                pass
                
    # 🎯【就是加在這裡！】處理完綠界的 POST 資料後，一腳把顧客踢去歷史點餐紀錄頁面！
    # ⚠️ 注意：請把 'order_history' 換成你專案中顧客看歷史紀錄那條路由的 name
    # 如果你不知道叫什麼，看你下一張圖的網址如果是 /order_history/ 或是 /history/，通常名字就叫 'order_history' 
    return redirect('order_history')

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
def complete_order(request, order_id):
    # 找到訂單，並把狀態從「準備中」改成「準備完成」
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'paid':
        order.status = 'completed'
        order.save()
    return redirect('kitchen_dashboard')
    
def create_order(request):
    if request.method == "POST":
        pickup_hour_str = request.POST.get('pickup_hour') # 例如 "10:24"
        
        if pickup_hour_str:
            hour = int(pickup_hour_str.split(':')[0])
            # 🎯 檢查：如果小於 11 點或大於 21 點
            if hour < 11 or hour > 21:
                messages.error(request, "超出營業時間，取餐時間請選擇 11:00 ~ 21:00 之間！")
                return redirect('order_cart_page')
def brand_story(request):
    return render(request,'brand_story.html')
def contact_us (request):
    return render(request,'contact_us.html')


@login_required(login_url='/user_login/') # 🌟 加上這行！沒登入就踢去登入頁（網址請改成你的登入網址）
def book_table(request):


    user_full_name = f"{request.user.last_name}{request.user.first_name}"
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['user'] = request.user.id
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user # 🌟 因為有上面那行，這裡 100% 能抓到 request.user，絕對不會出錯！
            reservation.save()
            messages.success(request, '訂位成功！')
            return redirect('book_table')
    
    else:
        # 因為絕對是會員，直接自動帶入資料
        initial_data = {
            'name': user_full_name,
            'phone': getattr(request.user, 'phone', ''),
            'email': request.user.email,
        }
        form = ReservationForm(initial=initial_data)
        
    return render(request, 'book_table.html', {'form': form})