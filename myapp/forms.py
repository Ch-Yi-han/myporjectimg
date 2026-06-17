import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password # 💡 引入 Django 的加密大師
from .models import CustomMember,Reservation
from django.contrib.auth.hashers import check_password
from datetime import datetime

class CustomRegisterForm(forms.ModelForm):
    password = forms.CharField(label='密碼', widget=forms.PasswordInput(attrs={'placeholder': '請輸入密碼'}))
    password_confirm = forms.CharField(label='確認密碼', widget=forms.PasswordInput(attrs={'placeholder': '請再次輸入密碼'}))

    class Meta:
        model = CustomMember
        fields = ['username', 'last_name', 'first_name','email','phone', 'birthday', 'gender', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': '請輸入自訂帳號'}),
            'last_name': forms.TextInput(attrs={'placeholder': '陳'}),
            'first_name': forms.TextInput(attrs={'placeholder': '小明'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@mail.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '0912345678'}),
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }

    # 檢查帳號是否重複
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomMember.objects.filter(username=username).exists():
            raise ValidationError('這個帳號已經被注冊過了！')
        return username

    # 檢查兩次密碼
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password != password_confirm:
            self.add_error('password_confirm', '兩次輸入的密碼不一致。')
        return cleaned_data

    # 儲存時攔截密碼，加密後再存入資料庫
    def save(self, commit=True):
        member = super().save(commit=False)
        member.password = make_password(self.cleaned_data['password'])
        if commit:
            member.save()
        return member

class UpdateProfileAndConfirmForm(forms.ModelForm):
    # 手動增加密碼相關欄位（非 Model 欄位）
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
        # 你的基本資料欄位
        fields = ['last_name', 'first_name', 'email', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 幫基本資料欄位也加上 Bootstrap 樣式
        for field in ['last_name', 'first_name', 'email', 'phone']:
            if field in self.fields:
                self.fields[field].widget.attrs.update({'class': 'form-control'})

    # 驗證邏輯
    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        # 1. 驗證目前的舊密碼是否正確
        # 注意：假設你的自訂 Model 密碼欄位叫 password，且資料庫存的是雜湊值
        if old_password and not check_password(old_password, self.instance.password):
            self.add_error('old_password', '目前密碼輸入錯誤')

        # 2. 如果使用者有輸入新密碼，進行新密碼的檢查
        if new_password or confirm_password:
            if new_password != confirm_password:
                self.add_error('confirm_password', '兩次輸入的新密碼不一致')
            


        return cleaned_data

    # 儲存邏輯
    def save(self, commit=True):
        member = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        
        # 如果使用者有填寫新密碼，將新密碼加密後存入
        if new_password:
            member.password = make_password(new_password)
            
        if commit:
            member.save()
        return member

def generate_time_slots():
    """自動產生 11:00 到 21:00，每 15 分鐘一格的選項"""
    choices = []
    start_hour = 11
    end_hour = 20
    
    # 轉換成當天的 datetime 物件方便做加法運算
    for hour in range(start_hour, end_hour + 1):
        for minute in ['00','15','30','45']:
            # 晚上最後一個時段通常不提供訂位（例如 21:30），所以卡到 21:30 就跳出
            if hour == end_hour and minute == '00':
                break
            time_str = f"{hour:02d}:{minute}"
            choices.append((time_str, time_str))
            
    return choices

class ReservationForm(forms.ModelForm):
    # 🌟 將 time_slot 改成 ChoiceField，並動態載入剛剛生成的 15 分鐘時段
    time_slot = forms.ChoiceField(
        choices=[], 
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="用餐時段"
    )

    class Meta:
        model = Reservation
        fields = ['user','name', 'phone', 'email', 'date', 'time_slot', 'guests', 'notes']
        widgets = {
            'user': forms.HiddenInput(),
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'min': datetime.today().strftime('%Y-%m-%d')
            }),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請輸入姓名'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：0912345678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '例：example@mail.com'}),
            'guests': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '若有嬰兒椅等需求請註記...'}),
        }

    # 🌟 表單初始化時，動態把時段塞進去
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['time_slot'].choices = generate_time_slots()

    # 容量驗證（維持原樣，但此時 time_slot 傳進來的是字串如 "11:15"）
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time_slot = cleaned_data.get('time_slot')
        guests = cleaned_data.get('guests')

        if date and time_slot and guests:
            available_seats = Reservation.get_available_seats(date, time_slot)
            if guests > available_seats:
                raise forms.ValidationError(
                    f"不好意思，該時段（{time_slot}）位置不足！目前僅剩 {available_seats} 個座位。"
                )
        return cleaned_data