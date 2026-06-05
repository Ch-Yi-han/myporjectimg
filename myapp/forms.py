import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password # 💡 引入 Django 的加密大師
from .models import CustomMember

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