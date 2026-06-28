import re
from django import forms
from django.core.exceptions import ValidationError
# make_password：將明文密碼轉成安全的雜湊值後再存入資料庫
from django.contrib.auth.hashers import make_password
from .models import CustomMember,Reservation
# check_password：比對使用者輸入的密碼與資料庫中的雜湊密碼
from django.contrib.auth.hashers import check_password
from datetime import datetime

class CustomRegisterForm(forms.ModelForm):
    """會員註冊表單：收集會員資料、確認密碼，並在儲存前加密密碼。"""

    # password_confirm 只用來核對密碼，不是 CustomMember 資料表的欄位
    password = forms.CharField(label='密碼', widget=forms.PasswordInput(attrs={'placeholder': '請輸入密碼'}))
    password_confirm = forms.CharField(label='確認密碼', widget=forms.PasswordInput(attrs={'placeholder': '請再次輸入密碼'}))
    last_name = forms.CharField(max_length=150, required=True, label="姓氏")
    first_name = forms.CharField(max_length=30, required=True, label="名字")

    class Meta:
        # 指定此 ModelForm 對應的資料模型
        model = CustomMember
        # 決定表單要顯示及提交哪些 Model 欄位
        fields = ['username', 'last_name', 'first_name','email','phone', 'birthday', 'gender', 'password']
        # widgets 只負責控制欄位在 HTML 中的輸入元件與外觀
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': '請輸入自訂帳號'}),
            'last_name': forms.TextInput(attrs={'placeholder': '陳'}),
            'first_name': forms.TextInput(attrs={'placeholder': '小明'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@mail.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '0912345678'}),
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_username(self):
        """驗證 username 欄位，避免註冊已存在的帳號。"""
        username = self.cleaned_data.get('username')
        if CustomMember.objects.filter(username=username).exists():
            raise ValidationError('這個帳號已經被注冊過了！')
        return username

    def clean(self):
        """執行跨欄位驗證，確認兩次輸入的密碼相同。"""
        # 先呼叫父類別的 clean()，取得已通過個別欄位驗證的資料
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password != password_confirm:
            # 將錯誤訊息顯示在「確認密碼」欄位旁
            self.add_error('password_confirm', '兩次輸入的密碼不一致。')
        return cleaned_data

    def save(self, commit=True):
        """先加密密碼，再決定是否立刻將會員資料寫入資料庫。"""
        # commit=False 先建立物件但不寫入資料庫，讓我們能先處理密碼
        member = super().save(commit=False)
        member.password = make_password(self.cleaned_data['password'])
        if commit:
            member.save()
        return member

class UpdateProfileAndConfirmForm(forms.ModelForm):
    """會員資料修改表單：修改基本資料，也可選擇更新密碼。"""

    # 以下三個欄位是表單額外欄位，不會直接對應到 Model 的資料表欄位
    old_password = forms.CharField(
        label="目前密碼", 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    new_password = forms.CharField(
        label="新密碼（如不修改請留空）", 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    confirm_password = forms.CharField(
        label="確認新密碼", 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = CustomMember
        # 只有這些基本資料會由 ModelForm 自動寫回 CustomMember
        fields = ['last_name', 'first_name', 'email', 'phone']

    def __init__(self, *args, **kwargs):
        """表單建立時，替基本資料欄位加入 Bootstrap 樣式。"""
        super().__init__(*args, **kwargs)
        for field in ['last_name', 'first_name', 'email', 'phone']:
            if field in self.fields:
                self.fields[field].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        """驗證舊密碼，並確認兩次輸入的新密碼一致。"""
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        # 將使用者輸入的舊密碼與目前會員資料庫中的雜湊密碼進行比對
        if old_password and not check_password(old_password, self.instance.password):
            self.add_error('old_password', '目前密碼輸入錯誤')

        # 任一新密碼欄位有內容時，就要求兩個欄位必須相同
        if new_password or confirm_password:
            if new_password != confirm_password:
                self.add_error('confirm_password', '兩次輸入的新密碼不一致')

        return cleaned_data

    def save(self, commit=True):
        """儲存基本資料；有填新密碼時，也會加密並更新密碼。"""
        member = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        
        # 沒有輸入新密碼時，保留資料庫中原有的密碼
        if new_password:
            member.password = make_password(new_password)
            
        if commit:
            member.save()
        return member

def generate_time_slots():
    """產生訂位時段選項，每 15 分鐘一個時段。"""
    choices = []
    start_hour = 11
    end_hour = 20
    
    # 外層逐小時、內層逐 15 分鐘產生時間字串
    for hour in range(start_hour, end_hour + 1):
        for minute in ['00','15','30','45']:
            # 到達 20:00 時停止，因此目前最後一個可選時段是 19:45
            if hour == end_hour and minute == '00':
                break
            time_str = f"{hour:02d}:{minute}"
            # ChoiceField 的選項格式為 (實際送出的值, 顯示文字)
            choices.append((time_str, time_str))
            
    return choices

class ReservationForm(forms.ModelForm):
    """訂位表單：收集訂位資料，並檢查所選時段的剩餘座位。"""

    # user 會隨表單送出，但用 HiddenInput 隱藏，不讓使用者自行選會員
    user = forms.ModelChoiceField(
        queryset=CustomMember.objects.all(),
        widget=forms.HiddenInput(),
        required=False
    )

    date = forms.DateField(
        # 同時接受 2026-06-24 與 2026/06/24 兩種日期格式
        input_formats=['%Y-%m-%d', '%Y/%m/%d'],
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            # HTML 日期選擇器不能選今天以前的日期
            'min': datetime.today().strftime('%Y-%m-%d')
        }),
        label="用餐日期"
    )

    time_slot = forms.ChoiceField(
        # 先保留空選項，會在 __init__ 中動態產生時段
        choices=[], 
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="用餐時段"
    )

    class Meta:
        model = Reservation
        # 指定訂位表單中會出現及儲存的欄位
        fields = ['user', 'name', 'phone', 'email', 'date', 'time_slot', 'guests', 'notes']
        # 設定各欄位的 Bootstrap 樣式、輸入限制和提示文字
        widgets = {
            'user': forms.HiddenInput(),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請輸入姓名'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：0912345678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '例：example@mail.com'}),
            'guests': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '若有嬰兒椅等需求請註記...'}),
        }

    def __init__(self, *args, **kwargs):
        """每次建立表單時，載入最新定義的可選訂位時段。"""
        super().__init__(*args, **kwargs)
        self.fields['time_slot'].choices = generate_time_slots()

    def clean(self):
        """取得日期、時段與人數，驗證餐廳是否仍有足夠座位。"""
        cleaned_data = super().clean()
        
        # 正常先從驗證後的 cleaned_data 取得；取不到時再讀取原始表單資料
        date = cleaned_data.get('date') or self.data.get('date')
        time_slot = cleaned_data.get('time_slot') or self.data.get('time_slot')
        guests = cleaned_data.get('guests') or self.data.get('guests')

        # 原始表單資料是字串，轉成整數後才能與剩餘座位數比較
        if guests:
            guests = int(guests)

        # 偵錯資訊會顯示在執行 Django 的終端機中
        print(f"【偵錯追蹤】日期：{date}，時段：{time_slot}，人數：{guests}")

        if date and time_slot and guests:
            # 呼叫 Reservation Model 的方法，查詢該日期與時段剩餘幾個座位
            available_seats = Reservation.get_available_seats(date, time_slot)
            print(f"【偵錯追蹤】該時段剩餘座位：{available_seats}")
            
            if guests > available_seats:
                # 座位不足屬於整份表單的錯誤，因此使用 forms.ValidationError
                raise forms.ValidationError(
                    f"不好意思，該時段（{time_slot}）位置不足！目前僅剩 {available_seats} 個座位。"
                )
                
        return cleaned_data
