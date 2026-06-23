from django.shortcuts import render, redirect, get_object_or_404  # 說明：提供渲染模板、重新導向、查不到資料時回傳 404 的常用 shortcut。
from .forms import CustomRegisterForm, UpdateProfileAndConfirmForm, ReservationForm  # 說明：匯入註冊、會員資料修改、訂位表單。
from django.contrib.auth import authenticate, login, logout as django_logout  # 說明：匯入 Django 內建登入驗證、登入與登出功能，並將 logout 取別名避免和自訂函式撞名。
from django.contrib import messages  # 說明：匯入訊息框架，用來在 redirect 後顯示成功或錯誤提示。
import random  # 說明：產生忘記密碼用的六位數隨機驗證碼。
from django.core.mail import send_mail  # 說明：用來寄送忘記密碼、付款成功、訂位成功等通知信。
from .models import CustomMember, Dish, CartItem, Order, OrderItem, Reservation,FinancialCategory,FinancialRecord  # 說明：匯入本專案會用到的會員、餐點、購物車、訂單、訂單明細與訂位模型。
from django.utils import timezone  # 說明：處理具時區資訊的時間，避免 naive datetime 問題。
from datetime import datetime  # 說明：用來解析取餐日期與時間字串，也用於產生綠界交易時間。
from django.views.decorators.csrf import csrf_exempt  # 說明：讓綠界付款回呼可以略過 CSRF 檢查，因為它是外部系統 POST 回來。
from django.http import HttpResponse, JsonResponse  # 說明：HttpResponse 回傳 HTML 或純文字，JsonResponse 回傳 AJAX 用 JSON。
from django.contrib.auth.decorators import login_required  # 說明：限制部分頁面必須登入後才能使用。
from django.conf import settings  # 說明：讀取 settings.py 內的 Email 等專案設定。
from django.utils.timezone import localtime  # 說明：把資料庫時間轉成目前時區時間，常用在通知信顯示。
from ecpay_payment_sdk import ECPayPaymentSdk  # 說明：匯入綠界付款 SDK，用來建立付款訂單與產生付款表單。


# ==========================================
# 首頁與靜態頁面
# ==========================================
def index(request):
    """首頁：使用 Django 官方認證機制"""
    # 💡 說明：因為 Django 內建會自動把 user 物件傳給所有 HTML 範本，
    # 除非你的首頁有其他額外的資料要撈（例如最新消息、推薦菜色），
    # 否則這裡可以保持超級乾淨，連 context 都不用帶！
    
    return render(request, 'index.html')


def menu(request):
    """菜單頁：顯示所有餐點資料，並提供登入狀態給模板使用。"""
    member_name = request.session.get('member_name')  # 說明：從 session 取得會員名稱，用於頁首顯示。
    dishes_data = Dish.objects.all()  # 說明：從資料庫查詢全部餐點資料。
    context = {  # 說明：整理菜單頁需要的模板資料。
        'is_login': member_name is not None,  # 說明：判斷目前是否有登入資訊。
        'member_name': member_name,  # 說明：傳給前端顯示會員名稱。
        'dishes': dishes_data  # 說明：傳給前端迴圈顯示餐點卡片。
    }
    return render(request, 'menu.html', context)  # 說明：渲染菜單頁。


def brand_story(request):
    """品牌故事頁：顯示餐廳品牌故事靜態頁面。"""
    return render(request, 'brand_story.html')  # 說明：不需要額外資料，直接渲染品牌故事模板。


def contact_us(request):
    """聯絡我們頁：顯示餐廳聯絡資訊靜態頁面。"""
    return render(request, 'contact_us.html')  # 說明：不需要額外資料，直接渲染聯絡我們模板。


# ==========================================
# 會員註冊、登入、登出與個人資料
# ==========================================
def user_login(request):
    """登入功能：接收帳號密碼，驗證成功後登入並導回首頁。"""
    error_message = None  # 說明：預設沒有錯誤訊息，登入失敗時才填入文字。

    if request.method == 'POST':  # 說明：只有表單送出時才進行帳號密碼驗證。
        user_input_name = request.POST.get('username')  # 說明：取得使用者輸入的帳號。
        user_input_pwd = request.POST.get('password')  # 說明：取得使用者輸入的密碼。

        user = authenticate(request, username=user_input_name, password=user_input_pwd)  # 說明：使用 Django 官方機制驗證帳號與加密密碼。

        if user is not None:  # 說明：驗證成功時會取得使用者物件。
            login(request, user)  # 說明：建立登入狀態，Django 會處理 session 與 request.user。
            return redirect('index')  # 說明：登入成功後導回首頁。

        error_message = "帳號或密碼錯誤！"  # 說明：驗證失敗時把錯誤訊息傳回登入頁。

    return render(request, 'user_login.html', {'error_message': error_message})  # 說明：GET 或登入失敗時顯示登入頁。


def register(request):
    """註冊功能：建立會員、加密密碼、儲存後自動登入。"""
    if request.method == 'POST':  # 說明：使用者送出註冊表單時處理資料。
        form = CustomRegisterForm(request.POST)  # 說明：把 POST 資料放入自訂註冊表單做驗證。

        if form.is_valid():  # 說明：確認所有欄位都符合表單規則。
            user = form.save(commit=False)  # 說明：先建立會員物件但暫時不寫入資料庫，方便先處理密碼。
            user.set_password(form.cleaned_data['password'])  # 說明：把明文密碼轉成 Django 安全的雜湊密碼。
            user.save()  # 說明：把會員資料正式寫入資料庫。
            login(request, user)  # 說明：註冊成功後直接登入，讓使用者不用再手動登入一次。
            return redirect('index')  # 說明：註冊並登入成功後回首頁。
    else:
        form = CustomRegisterForm()  # 說明：GET 請求時建立空白註冊表單。

    return render(request, 'register.html', {'form': form})  # 說明：顯示註冊頁，若表單驗證失敗也會帶著錯誤訊息回來。


def logout(request):
    """登出功能：登出 Django 使用者並清除舊版 session 登入資訊。"""
    django_logout(request)  # 說明：呼叫 Django 官方登出，清除 request.user 的登入狀態。

    if 'member_id' in request.session:  # 說明：若舊版登入流程曾存 member_id，登出時一併清除。
        del request.session['member_id']  # 說明：刪除 session 中的會員 id。
    if 'member_name' in request.session:  # 說明：若舊版登入流程曾存 member_name，登出時一併清除。
        del request.session['member_name']  # 說明：刪除 session 中的會員名稱。

    messages.success(request, '您已成功登出！')  # 說明：設定登出成功提示，下一頁可顯示。
    return redirect('index')  # 說明：登出後回首頁。


@login_required(login_url='/user_login/')  # 說明：未登入者不能修改個人資料，會被導向登入頁。
def edit_profile(request):
    """編輯會員資料：讓登入會員修改個人資料，若修改密碼會重新加密並維持登入。"""
    member = request.user  # 說明：目前登入的使用者物件就是要編輯的會員資料。

    if request.method == 'POST':  # 說明：表單送出時更新會員資料。
        form = UpdateProfileAndConfirmForm(request.POST, instance=member)  # 說明：用 POST 資料更新目前會員 instance。

        if form.is_valid():  # 說明：確認表單欄位資料合法。
            user = form.save(commit=False)  # 說明：先取得更新後的會員物件，暫不寫入資料庫。

            if 'password' in form.cleaned_data and form.cleaned_data['password']:  # 說明：如果表單有填新密碼，才需要重新設定密碼。
                user.set_password(form.cleaned_data['password'])  # 說明：把新密碼轉成雜湊後再保存。

            user.save()  # 說明：儲存會員資料更新。

            from django.contrib.auth import update_session_auth_hash  # 說明：密碼修改後更新 session，避免使用者被強制登出。
            update_session_auth_hash(request, user)  # 說明：刷新目前 session 的驗證雜湊。

            messages.success(request, '個人資料已成功更新！')  # 說明：設定更新成功提示。
            return redirect('edit_profile')  # 說明：更新後回到個人資料頁。
    else:
        form = UpdateProfileAndConfirmForm(instance=member)  # 說明：GET 請求時用目前會員資料建立表單初始值。

    return render(request, 'edit_profile.html', {'form': form})  # 說明：渲染個人資料編輯頁。


def get_current_member(request):
    """取得目前會員：從舊版 session 的 member_id 查詢會員，找不到則回傳 None。"""
    member_id = request.session.get('member_id')  # 說明：從 session 取得會員 id。

    if not member_id:  # 說明：沒有會員 id 代表沒有舊版登入資訊。
        return None  # 說明：直接回傳 None，表示目前查不到會員。

    try:
        return CustomMember.objects.get(id=member_id)  # 說明：用會員 id 查詢會員資料。
    except CustomMember.DoesNotExist:
        return None  # 說明：若資料庫找不到該會員，也回傳 None。


# ==========================================
# 忘記密碼流程
# ==========================================
def forgot_password_request(request):
    """忘記密碼第一步：確認帳號與 Email，產生驗證碼並寄到信箱。"""
    if request.method == "POST":  # 說明：使用者送出帳號與 Email 時才處理驗證。
        username = request.POST.get('username')  # 說明：取得使用者輸入的帳號。
        email = request.POST.get('email')  # 說明：取得使用者輸入的 Email。

        try:
            user = CustomMember.objects.get(username=username, email=email)  # 說明：確認帳號與 Email 是否同時符合同一個會員。
            code = str(random.randint(100000, 999999))  # 說明：產生六位數驗證碼並轉成字串。

            request.session['reset_code'] = code  # 說明：把驗證碼存在 session，供下一步比對。
            request.session['reset_user_id'] = user.id  # 說明：保存要重設密碼的會員 id。
            request.session.set_expiry(300)  # 說明：設定 session 五分鐘後過期，限制驗證碼有效時間。

            send_mail(  # 說明：寄出密碼重設驗證碼。
                '【聚福樓】您的密碼重設驗證碼 🔐',  # 說明：信件主旨。
                f'親愛的會員您好：\n\n您的密碼重設驗證碼為：【 {code} 】\n\n此驗證碼將於 5 分鐘後過期，請儘速回到網頁輸入完成驗證。\n\n聚福樓團隊 敬上',  # 說明：信件內容，包含驗證碼與有效時間。
                settings.EMAIL_HOST_USER,  # 說明：寄件者使用 settings.py 設定的信箱。
                [email],  # 說明：收件者為使用者輸入並已驗證的 Email。
                fail_silently=False  # 說明：寄信失敗時拋出錯誤，方便發現設定問題。
            )

            messages.success(request, "驗證碼已發送到您的信箱，請至信箱查收！")  # 說明：通知使用者去信箱收驗證碼。
            return redirect('verify_code')  # 說明：進入驗證碼輸入頁。

        except CustomMember.DoesNotExist:
            messages.error(request, "帳號或是電子信箱不正確，請重新確認。")  # 說明：帳號或 Email 不匹配時顯示錯誤。

    return render(request, 'forgot_password_request.html')  # 說明：顯示忘記密碼第一步頁面。


def verify_code(request):
    """忘記密碼第二步：比對使用者輸入的驗證碼是否正確。"""
    if 'reset_code' not in request.session:  # 說明：若 session 沒有驗證碼，表示尚未申請或已過期。
        messages.error(request, "驗證碼已失效，請重新申請")  # 說明：提示使用者重新取得驗證碼。
        return redirect('forgot_password_request')  # 說明：導回忘記密碼第一步。

    if request.method == "POST":  # 說明：使用者送出驗證碼時才比對。
        input_code = request.POST.get('code')  # 說明：取得使用者輸入的驗證碼。
        session_code = request.session.get('reset_code')  # 說明：取得 session 中保存的正確驗證碼。

        if input_code == session_code:  # 說明：驗證碼相同代表驗證通過。
            request.session['code_verified'] = True  # 說明：在 session 標記已通過驗證。
            return redirect('reset_password')  # 說明：導向重設密碼頁。

        messages.error(request, "驗證碼錯誤，請重新輸入")  # 說明：驗證碼不一致時顯示錯誤。
        return redirect('verify_code')  # 說明：留在驗證碼頁重新輸入。

    return render(request, 'verify_code.html')  # 說明：GET 請求時顯示驗證碼輸入頁。


def reset_password(request):
    """忘記密碼第三步：驗證通過後更新會員密碼（最高防禦安全結合版）"""
    
    # 🛡️ 1. 第一關安全防禦：檢查他有沒有乖乖走完驗證碼步驟
    if not request.session.get('code_verified'):
        messages.error(request, "請先完成驗證")
        return redirect('forgot_password_request')

    # 🛡️ 2. 第二關安全防禦：取得要重設密碼的會員 id，沒有就代表 session 過期了
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, "重設密碼流程已失效，請重新申請")
        return redirect('forgot_password_request')

    if request.method == "POST":
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # 🛡️ 3. 第三關安全防禦：避免繞過前端檢查送出空密碼
        if not password or not password_confirm:
            messages.error(request, "請輸入新密碼與確認密碼")
            return render(request, 'reset_password.html')

        # 🛡️ 4. 第四關安全防禦：比對兩次輸入密碼是否相同
        if password != password_confirm:
            messages.error(request, "兩次輸入的密碼不相同")
            return render(request, 'reset_password.html')

        # 🛡️ 5. 第五關安全防禦：去資料庫撈出會員，並加上 try-except 防止帳號中途被刪除導致網頁噴 500
        try:
            user = CustomMember.objects.get(id=user_id)
        except CustomMember.DoesNotExist:
            messages.error(request, "此帳號不存在，重設密碼流程已失效")
            return redirect('forgot_password_request')

        # 🟢 6. 核心密碼變更與加密
        user.set_password(password)  # 轉成 Django 安全雜湊
        user.save()                  # 🌟 記得一定要 save() 才會寫進資料庫！

        # 🟢 7. 官方認證大絕：密碼改成功，免重新登入，直接核發官方護照！
        login(request, user)

        # 🟢 8. 清除忘記密碼專用的過期 Session 鑰匙，保障資安
        session_keys = ['reset_code', 'reset_user_id', 'code_verified']
        for key in session_keys:
            if key in request.session:
                del request.session[key]

        # 🟢 9. 完美絲滑導向聚福樓首頁
        messages.success(request, "密碼修改成功！已自動為您登入聚福樓會員。")
        return redirect('index') 

    return render(request, 'reset_password.html')  # 用於 GET 請求時顯示表單

# ==========================================
# 線上點餐與購物車
# ==========================================
def order_online(request):
    """線上點餐頁：顯示所有餐點，並依登入狀態顯示會員名稱。"""
    member_name = None  # 說明：預設沒有會員名稱，未登入時保持 None。

    if request.user.is_authenticated:  # 說明：使用 Django 官方登入狀態判斷目前是否已登入。
        member = request.user  # 說明：取得目前登入會員。

        if member.last_name or member.first_name:  # 說明：如果會員有填姓名，就使用姓與名組合。
            member_name = f"{member.last_name}{member.first_name}"  # 說明：組合完整姓名。
        else:
            member_name = member.username  # 說明：沒有姓名時改用帳號作為顯示名稱。

    dishes = Dish.objects.all()  # 說明：查詢所有餐點資料，供前端顯示可點餐項目。

    return render(request, 'order_online.html', {  # 說明：渲染線上點餐頁並傳入餐點與會員資訊。
        'dishes': dishes,  # 說明：餐點清單。
        'member_name': member_name,  # 說明：會員顯示名稱。
        'is_login': request.user.is_authenticated  # 說明：前端用來判斷是否顯示會員狀態或限制操作。
    })


def add_to_cart(request):
    """加入購物車：接收 AJAX POST 的餐點 id 與數量，建立或累加購物車項目。"""
    if not request.user.is_authenticated:  # 說明：未登入者不能加入購物車。
        return JsonResponse({  # 說明：回傳 JSON 給前端 AJAX 使用。
            'status': 'error',
            'message': '請先登入會員，才能開始點餐喔！'
        })

    if request.method == 'POST':  # 說明：只有 POST 請求才視為加入購物車操作。
        item_id = request.POST.get('item_id')  # 說明：取得前端傳來的餐點 id。
        quantity = int(request.POST.get('quantity', 1))  # 說明：取得數量，若沒傳則預設為 1。
        member = request.user  # 說明：取得目前登入會員，作為購物車資料的歸屬者。

        try:
            dish = Dish.objects.get(id=item_id)  # 說明：依餐點 id 查詢餐點資料。

            cart_item, created = CartItem.objects.get_or_create(  # 說明：找出既有購物車項目；沒有則建立新的。
                member=member,  # 說明：購物車項目屬於目前會員。
                item=dish,  # 說明：購物車項目對應目前餐點。
                defaults={'quantity': quantity}  # 說明：新建立時使用前端傳來的數量。
            )

            if not created:  # 說明：如果購物車裡已經有同一道餐點，就累加數量。
                cart_item.quantity += quantity  # 說明：原本數量加上這次新增數量。
                cart_item.save()  # 說明：儲存更新後的購物車數量。

            cart_count = CartItem.objects.filter(member=member).count()  # 說明：計算目前會員購物車有幾筆項目，給前端更新數字。

            return JsonResponse({  # 說明：加入成功後回傳成功狀態與購物車數量。
                'status': 'success',
                'cart_count': cart_count
            })

        except Dish.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '找不到該項餐點'})  # 說明：餐點 id 不存在時回傳錯誤。

    return JsonResponse({'status': 'error', 'message': '無效的請求方式'})  # 說明：非 POST 請求一律視為無效。


@login_required(login_url='/user_login/')  # 說明：購物車頁只允許登入會員查看。
def view_cart(request):
    """查看購物車：列出會員購物車內容，計算小計、總金額，並產生取餐時間選項。"""
    member = request.user  # 說明：取得目前登入會員。

    if member.last_name or member.first_name:  # 說明：優先使用會員姓名顯示。
        member_name = f"{member.last_name}{member.first_name}"  # 說明：組合姓與名。
    else:
        member_name = member.username  # 說明：沒有姓名時顯示帳號。

    cart_items = CartItem.objects.filter(member=member)  # 說明：查詢目前會員所有購物車項目。

    for item in cart_items:  # 說明：逐筆計算商品小計，供模板直接顯示。
        item.subtotal = item.item.price * item.quantity  # 說明：小計等於餐點單價乘上數量。

    total_amount = sum(cart_item.item.price * cart_item.quantity for cart_item in cart_items)  # 說明：加總所有購物車項目的金額。

    START_HOUR = 11  # 說明：可取餐起始小時為 11 點。
    END_HOUR = 21  # 說明：可取餐結束小時為 21 點。
    TIME_INTERVAL = 15  # 說明：取餐時間每 15 分鐘一個選項。

    time_choices = []  # 說明：存放可選取餐時間字串。
    for hour in range(START_HOUR, END_HOUR + 1):  # 說明：從起始小時跑到結束小時。
        for minute in range(0, 60, TIME_INTERVAL):  # 說明：每小時以 15 分鐘為間隔產生選項。
            if hour == END_HOUR and minute > 0:  # 說明：結束小時只保留整點，避免產生 21:15 之後的時間。
                continue
            time_str = f"{hour:02d}:{minute:02d}"  # 說明：把時間格式化成兩位數，例如 09:15。
            time_choices.append(time_str)  # 說明：加入時間選項清單。

    context = {  # 說明：整理購物車頁面需要的所有模板資料。
        'cart_items': cart_items,  # 說明：購物車項目。
        'total_amount': total_amount,  # 說明：購物車總金額。
        'member_name': member_name,  # 說明：會員顯示名稱。
        'is_login': True,  # 說明：能進入此頁代表一定已登入。
        'time_choices': time_choices,  # 說明：可選取餐時間清單。
    }

    return render(request, 'view_cart.html', context)  # 說明：渲染購物車頁。


@login_required(login_url='/user_login/')  # 說明：只有登入會員能修改自己的購物車。
def update_cart_quantity(request, item_id, action):
    """更新購物車數量：依 increase 或 decrease 調整數量，歸零時刪除項目並回傳 JSON。"""
    member = request.user  # 說明：取得目前登入會員。
    cart_item = get_object_or_404(CartItem, member=member, item_id=item_id)  # 說明：查詢該會員購物車中的指定餐點，找不到則回傳 404。

    if action == 'increase':  # 說明：增加數量操作。
        cart_item.quantity += 1  # 說明：數量加 1。
        cart_item.save()  # 說明：儲存新數量。
    elif action == 'decrease':  # 說明：減少數量操作。
        cart_item.quantity -= 1  # 說明：數量減 1。

        if cart_item.quantity <= 0:  # 說明：數量小於等於 0 時代表要移除商品。
            cart_item.delete()  # 說明：刪除該購物車項目。
            return JsonResponse({'status': 'deleted', 'item_id': item_id})  # 說明：回傳已刪除狀態，前端可移除該列。

        cart_item.save()  # 說明：數量仍大於 0 時儲存更新。

    subtotal = cart_item.item.price * cart_item.quantity  # 說明：重新計算此商品小計。
    cart_items = CartItem.objects.filter(member=member)  # 說明：重新查詢會員購物車項目。
    total_amount = sum(item.item.price * item.quantity for item in cart_items)  # 說明：重新計算購物車總金額。

    return JsonResponse({  # 說明：回傳更新後資料給前端局部更新畫面。
        'status': 'success',
        'quantity': cart_item.quantity,
        'subtotal': subtotal,
        'total_amount': total_amount
    })


# ==========================================
# 結帳與訂單管理
# ==========================================
@login_required(login_url='/user_login/')  # 說明：只有登入會員可以結帳。
def checkout(request):
    """結帳建立訂單：把購物車內容轉成 Order 與 OrderItem，並清空購物車。"""
    member = request.user  # 說明：取得目前登入會員。
    cart_items = CartItem.objects.filter(member=member)  # 說明：查詢會員目前購物車內容。

    if not cart_items.exists():  # 說明：購物車為空時不能建立訂單。
        return redirect('view_cart')  # 說明：導回購物車頁。

    if request.method == 'POST':  # 說明：只有送出結帳表單才建立訂單。
        pickup_date_str = request.POST.get('pickup_date')  # 說明：取得前端送出的取餐日期，例如 2026-06-16。
        pickup_time_slot = request.POST.get('pickup_time_slot')  # 說明：取得前端送出的取餐時間，例如 18:30。

        pickup_datetime = timezone.now()  # 說明：預設取餐時間為現在，若前端有送日期時間會覆蓋。
        total_amount = sum(item.item.price * item.quantity for item in cart_items)  # 說明：計算訂單總金額。

        if pickup_date_str and pickup_time_slot:  # 說明：日期與時間都有值時才組合取餐時間。
            combined_str = f"{pickup_date_str} {pickup_time_slot}"  # 說明：組合成 datetime 可解析字串。
            naive_datetime = datetime.strptime(combined_str, "%Y-%m-%d %H:%M")  # 說明：把字串解析成沒有時區的 datetime。
            pickup_datetime = timezone.make_aware(naive_datetime)  # 說明：轉成 Django 可安全保存的有時區 datetime。

        order = Order.objects.create(  # 說明：建立訂單主檔。
            member=member,  # 說明：訂單歸屬於目前會員。
            total_amount=total_amount,  # 說明：保存訂單總金額。
            status='pending',  # 說明：初始狀態為待付款或待處理。
            pickup_time=pickup_datetime  # 說明：保存取餐時間。
        )

        for item in cart_items:  # 說明：把購物車每一項轉成訂單明細。
            OrderItem.objects.create(
                order=order,  # 說明：訂單明細連到剛建立的訂單主檔。
                item_name=item.item.name,  # 說明：保存餐點名稱，避免日後餐點改名影響歷史訂單。
                price=item.item.price,  # 說明：保存當下單價。
                quantity=item.quantity  # 說明：保存購買數量。
            )

        cart_items.delete()  # 說明：訂單建立後清空購物車。
        return redirect('order_history')  # 說明：結帳完成後導向訂單紀錄頁。

    return redirect('view_cart')  # 說明：非 POST 進入結帳時導回購物車。


@login_required(login_url='/user_login/')  # 說明：只有登入會員能查看自己的訂單紀錄。
def order_history(request):
    """訂單紀錄：列出目前登入會員的所有訂單，依建立時間由新到舊排序。"""
    member = request.user  # 說明：取得目前登入會員。
    orders = Order.objects.filter(member=member).order_by('-created_at')  # 說明：查詢該會員訂單，最新的排在前面。
    print(f"=== [歷史訂單偵錯] 成功幫 {member.username} 撈到 {orders.count()} 筆訂單！ ===")  # 說明：開發偵錯用，確認查到幾筆訂單。
    return render(request, 'order_history.html', {'orders': orders})  # 說明：渲染訂單紀錄頁。


@login_required(login_url='/user_login/')  # 說明：只有登入會員能刪除自己的訂單。
def delete_order(request, order_id):
    """刪除訂單：只允許會員刪除自己的未付款或 pending 訂單。"""
    member = request.user  # 說明：取得目前登入會員。
    order = get_object_or_404(Order, id=order_id, member=member)  # 說明：只查詢屬於目前會員的指定訂單。

    if order.status == '未付款' or order.status == 'pending':  # 說明：只有未付款或 pending 狀態可以刪除。
        order.delete()  # 說明：刪除訂單，相關明細若有 Cascade 會一起刪除。
        messages.success(request, "訂單已成功取消並刪除！")  # 說明：設定刪除成功提示。
    else:
        messages.error(request, "該訂單已進入製作或已付款，無法取消！")  # 說明：已付款或製作中不能刪除。

    return redirect('order_history')  # 說明：操作完成後回訂單紀錄頁。


# ==========================================
# 綠界付款流程
# ==========================================
@login_required(login_url='/user_login/')  # 說明：只有登入會員能前往付款。
def go_to_pay(request, order_id):
    """前往付款：建立綠界付款參數，產生自動送出的付款 HTML 表單。"""
    member = request.user  # 說明：取得目前登入會員。
    order = get_object_or_404(Order, id=order_id, member=member)  # 說明：確認訂單存在且屬於目前會員。

    ecpay_payment_sdk = ECPayPaymentSdk(  # 說明：初始化綠界測試環境 SDK。
        MerchantID='3002607',
        HashKey='pwFHCqoQZGmho4w6',
        HashIV='EkRm7iFT261dpevs'
    )

    YOUR_DOMAIN = "http://192.168.1.112:8080"  # 說明：綠界回呼與返回網址使用的網站網域。

    current_time = datetime.now()  # 說明：取得目前時間，產生交易編號與交易日期。
    trade_no = current_time.strftime("JFL%Y%m%d%H%M%S")  # 說明：產生綠界訂單編號。
    trade_date = current_time.strftime('%Y/%m/%d %H:%M:%S')  # 說明：產生綠界要求的交易日期格式。

    order.merchant_trade_no = trade_no  # 說明：把綠界交易編號存回訂單，供付款回呼時查詢訂單。
    order.save()  # 說明：儲存交易編號。

    client_parameters = {  # 說明：準備傳給綠界 SDK 的付款參數。
        'MerchantTradeNo': trade_no,  # 說明：綠界交易編號。
        'MerchantTradeDate': trade_date,  # 說明：交易建立時間。
        'PaymentType': 'aio',  # 說明：綠界 aio 固定付款類型。
        'TotalAmount': int(order.total_amount),  # 說明：付款金額，綠界要求整數。
        'TradeDesc': 'JufuLouShopOrderDescription',  # 說明：交易描述。
        'ItemName': 'JufuLouDeliciousMeal',  # 說明：付款項目名稱。
        'ReturnURL': f'{YOUR_DOMAIN}/ecpay_callback/',  # 說明：綠界伺服器背景通知付款結果的網址。
        'ChoosePayment': 'Credit',  # 說明：指定信用卡付款。
        'EncryptType': 1,  # 說明：使用 SHA256 加密檢查碼。
        'OrderResultURL': f'{YOUR_DOMAIN}/ecpay_return/',  # 說明：付款完成後使用者瀏覽器返回的網址。
    }

    try:
        final_params = ecpay_payment_sdk.create_order(client_parameters)  # 說明：讓 SDK 產生綠界需要的完整參數與 CheckMacValue。
        action_url = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'  # 說明：綠界測試付款頁網址。
        html_form = ecpay_payment_sdk.gen_html_post_form(action_url, final_params)  # 說明：產生會自動 POST 到綠界的 HTML 表單。
        return HttpResponse(html_form)  # 說明：直接把付款表單回傳給瀏覽器，導向綠界付款。
    except Exception as e:
        return HttpResponse(f'建立綠界訂單失敗: {e}')  # 說明：若 SDK 建立失敗，顯示錯誤內容。


@csrf_exempt  # 說明：綠界伺服器從外部 POST 回來，需免除 Django CSRF 檢查。
def ecpay_callback(request):
    """綠界付款通知：背景接收綠界付款結果，成功後更新訂單並回傳 1|OK。"""
    if request.method == 'POST':  # 說明：綠界通知使用 POST。
        ecpay_data = request.POST.dict()  # 說明：把綠界傳來的 POST 資料轉成一般 dict。
        rtn_code = ecpay_data.get('RtnCode')  # 說明：綠界付款結果代碼，1 代表付款成功。
        merchant_trade_no = ecpay_data.get('MerchantTradeNo')  # 說明：綠界回傳的交易編號。

        if rtn_code == '1':  # 說明：付款成功才更新訂單狀態。
            try:
                order = Order.objects.get(merchant_trade_no=merchant_trade_no)  # 說明：用交易編號找回本地訂單。
                order.status = 'preparing'  # 說明：背景通知成功後，將訂單狀態改為準備中。
                order.is_paid = True  # 說明：標記訂單已付款。
                order.save()  # 說明：保存付款狀態。
                return HttpResponse('1|OK')  # 說明：依綠界規格回覆成功，避免綠界重複通知。
            except Order.DoesNotExist:
                return HttpResponse('0|Order NotFound')  # 說明：找不到訂單時回傳失敗原因。

    return HttpResponse('0|Fail')  # 說明：非 POST 或付款失敗時回傳失敗。


@csrf_exempt  # 說明：綠界付款完成後從外部 POST 導回，也需要免除 CSRF 檢查。
def ecpay_return(request):
    """綠界付款結果頁：付款完成後更新訂單狀態，並寄送付款成功通知信。"""
    if request.method == 'POST':  # 說明：綠界返回結果通常以 POST 傳回。
        ecpay_data = request.POST.dict()  # 說明：取得綠界付款結果資料。
        rtn_code = ecpay_data.get('RtnCode')  # 說明：付款結果代碼。
        merchant_trade_no = ecpay_data.get('MerchantTradeNo')  # 說明：綠界交易編號。

        if rtn_code == '1':  # 說明：付款成功才更新資料與寄信。
            try:
                order = Order.objects.get(merchant_trade_no=merchant_trade_no)  # 說明：用交易編號查詢訂單。

                if order.status != 'paid':  # 說明：避免同一筆訂單重複處理與重複寄信。
                    order.status = 'paid'  # 說明：將訂單狀態改成已付款。
                    order.is_paid = True  # 說明：標記付款完成。
                    order.save()  # 說明：儲存訂單付款狀態。

                    subject = f'【聚福樓】線上點餐付款成功通知（訂單編號：{order.id}）'  # 說明：付款成功通知信主旨。
                    tw_time = localtime(order.pickup_time).strftime("%Y-%m-%d %H:%M")  # 說明：把取餐時間轉成台灣時區顯示格式。
                    message = (  # 說明：付款成功通知信內容。
                        f'親愛的聚福樓會員您好：\n\n'
                        f'我們已成功收到您的線上點餐款項！\n'
                        f'===============================\n'
                        f' 訂單編號：{order.id}\n'
                        f' 付款金額：NT$ {int(order.total_amount)} 元\n'
                        f' 預約取餐時間：{tw_time}\n'
                        f'===============================\n\n'
                        f'廚房已經收到您的訂單並開始全力製作，期待您的蒞臨取餐！'
                    )

                    user_email = order.member.email  # 說明：收件人使用訂單會員的 Email。

                    send_mail(  # 說明：寄送付款成功通知信。
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user_email],
                        fail_silently=True  # 說明：寄信失敗不讓付款返回頁中斷。
                    )
                    income_category, created = FinancialCategory.objects.get_or_create(
                        record_type='INCOME',
                        name='線上點餐收入'
                    )

                    # 2. 自動在流水帳裡塞入一筆對應這筆訂單的金額，完全免手動
                    FinancialRecord.objects.get_or_create(
                        order=order,
                        defaults={
                            'category': income_category,
                            'amount': order.total_amount,
                            'date': timezone.now().date(),
                            'note': f"顧客線上點餐自動入帳（訂單編號：{order.id}）"
                        }
                    )
            except Order.DoesNotExist:
                pass  # 說明：找不到訂單時略過，最後仍導回訂單紀錄頁。

    return redirect('order_history')  # 說明：處理完成後導向訂單紀錄頁。


# ==========================================
# 廚房後台
# ==========================================
def kitchen_dashboard(request):
    """廚房後台：列出已付款待製作訂單，以及最近完成的訂單。"""
    preparing_orders = Order.objects.filter(status='paid').prefetch_related('items').order_by('created_at')  # 說明：查詢待製作訂單，並預先載入訂單明細。
    completed_orders = Order.objects.filter(status='completed').prefetch_related('items').order_by('-id')[:10]  # 說明：查詢最近完成的 10 筆訂單。

    context = {  # 說明：整理廚房後台模板資料。
        'preparing_orders': preparing_orders,  # 說明：待製作訂單清單。
        'completed_orders': completed_orders,  # 說明：最近完成訂單清單。
    }
    return render(request, 'kitchen_dashboard.html', context)  # 說明：渲染廚房後台頁。


def complete_order(request, order_id):
    """完成訂單：廚房點擊完成後，將已付款訂單狀態改成 completed。"""
    order = get_object_or_404(Order, id=order_id)  # 說明：依訂單 id 查詢訂單，找不到則回傳 404。

    if order.status == 'paid':  # 說明：只有已付款、待製作訂單可以改成完成。
        order.status = 'completed'  # 說明：更新狀態為已完成。
        order.save()  # 說明：儲存訂單狀態。

    return redirect('kitchen_dashboard')  # 說明：完成後回廚房後台。


def create_order(request):
    """建立訂單時間檢查：示範檢查取餐時間是否在營業時間內。"""
    if request.method == "POST":  # 說明：只有表單送出時才檢查時間。
        pickup_hour_str = request.POST.get('pickup_hour')  # 說明：取得前端傳來的取餐時間字串，例如 10:24。

        if pickup_hour_str:  # 說明：有傳入取餐時間才進行檢查。
            hour = int(pickup_hour_str.split(':')[0])  # 說明：取出小時部分並轉成整數。

            if hour < 11 or hour > 21:  # 說明：營業時間限制為 11:00 到 21:00。
                messages.error(request, "超出營業時間，取餐時間請選擇 11:00 ~ 21:00 之間！")  # 說明：時間不合法時顯示錯誤。
                return redirect('order_cart_page')  # 說明：導回訂單或購物車頁重新選擇。


# ==========================================
# 線上訂位
# ==========================================
@login_required(login_url='/user_login/')  # 說明：只有登入會員可以線上訂位。
def book_table(request):
    """線上訂位：顯示訂位表單，送出後建立 Reservation 並寄送通知信。"""
    user_full_name = f"{request.user.last_name}{request.user.first_name}"  # 說明：組合目前會員姓名，作為訂位人姓名預設值。

    if request.method == 'POST':  # 說明：使用者送出訂位表單時建立訂位資料。
        form = ReservationForm(request.POST)  # 說明：用 POST 資料建立訂位表單並驗證。

        if form.is_valid():  # 說明：確認訂位欄位符合表單規則。
            reservation = form.save(commit=False)  # 說明：先取得訂位物件，暫不寫入資料庫。
            reservation.user = request.user  # 說明：把目前登入會員指定給訂位資料。
            reservation.save()  # 說明：正式保存訂位資料。

            try:
                subject = f'【聚福樓】您的中式料理訂位已確認（訂位編號：{reservation.id}）'  # 說明：訂位成功通知信主旨。
                message = (  # 說明：訂位成功通知信內容。
                    f'親愛的 {user_full_name} 貴賓您好：\n\n'
                    f'感謝您選擇聚福樓！我們已為您保留座位，期待您的光臨。\n'
                    f'===============================\n'
                    f' 訂位編號：{reservation.id}\n'
                    f' 訂位姓名：{user_full_name} 貴賓\n'
                    f' 訂位日期：{reservation.date}\n'
                    f' 訂位時間：{reservation.time_slot}\n'
                    f' 訂位人數：{reservation.guests} 位\n'
                    f'===============================\n\n'
                    f'※ 溫馨提醒：若需取消或變更訂位，請提前來電告知。謝謝您！'
                )

                user_email = request.user.email  # 說明：收件人使用目前登入會員的 Email。
                send_mail(  # 說明：寄出訂位成功通知信。
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_email],
                    fail_silently=True  # 說明：寄信失敗不影響使用者完成訂位。
                )
            except Exception as e:
                print(f"訂位成功信件發送失敗: {e}")  # 說明：寄信失敗只印出錯誤，不中斷訂位流程。

            messages.success(request, '訂位成功！')  # 說明：設定訂位成功提示。
            return redirect('book_table')  # 說明：送出成功後回到訂位頁。

        print(form.errors)  # 說明：表單驗證失敗時在伺服器端印出錯誤，方便開發除錯。
    else:
        initial_data = {  # 說明：GET 請求時準備表單初始值。
            'name': user_full_name,  # 說明：預填會員姓名。
            'phone': getattr(request.user, 'phone', ''),  # 說明：若會員有 phone 欄位就預填，沒有則留空。
            'email': request.user.email,  # 說明：預填會員 Email。
        }
        form = ReservationForm(initial=initial_data)  # 說明：建立帶有初始資料的訂位表單。

    return render(request, 'book_table.html', {'form': form})  # 說明：渲染訂位頁。


@login_required(login_url='/user_login/')  # 說明：只有登入會員可以查看自己的訂位紀錄。
def my_bookings(request):
    """我的訂位：查詢目前登入會員的所有訂位紀錄，依訂位日期由新到舊排序。"""
    bookings = Reservation.objects.filter(user=request.user).order_by('-date')  # 說明：查詢目前會員的訂位資料。
    return render(request, 'my_bookings.html', {'bookings': bookings})  # 說明：渲染我的訂位頁。


@login_required(login_url='/user_login/')  # 說明：只有登入會員可以取消自己的訂位。
def cancel_booking(request, booking_id):
    """取消訂位：確認訂位屬於目前登入會員後刪除。"""
    booking = get_object_or_404(Reservation, id=booking_id, user=request.user)  # 說明：查詢指定訂位，並確認它屬於目前會員。
    booking.delete()  # 說明：刪除訂位資料。
    messages.success(request, "您的訂位已成功取消！")  # 說明：設定取消成功提示。
    return redirect('my_bookings')  # 說明：取消後回到我的訂位頁。
