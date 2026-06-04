import re 
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import UserProfile


User = get_user_model()

class RegisterForm(forms.ModelForm):
    username = forms.CharField(
        label='帳號', 
        widget=forms.TextInput(attrs={'placeholder': '請輸入自訂帳號'})
    )
    email = forms.EmailField(
        label='電子信箱', 
        widget=forms.EmailInput(attrs={'placeholder': 'example@mail.com'})
    )
    password = forms.CharField(
        label='密碼',
        widget=forms.PasswordInput(attrs={'placeholder':'請輸入密碼'}),
        help_text='密碼必須至少8個字，且至少包含一個英文字母。'
    )
    password_confirm = forms.CharField(
        label= '確認密碼',
        widget=forms.PasswordInput(attrs={'placeholder':'請再次輸入密碼'})
    )

    class Meta:
        model = UserProfile
        fields = ['phone','birthday','gender']
        widgets={ 
            'phone':forms.TextInput(attrs={'placeholder':'請輸入電話號碼'}),
            'birthday':forms.DateInput(attrs={'type':'date'}),
        }

    def clean_password(self):
        password=self.cleaned_data.get('passowrd')
        
        if not password:
            return password
        

        if len(password)< 8:
            raise ValidationError('密碼長度必須超過8個字元。')
        
        if not re.search(r'[a-zA-Z]',password):
            raise ValidationError('密碼必須包含至少一個英文字母')
        
        return password
        
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm','兩次輸入密碼不一致')

        return cleaned_data
        
    def save(self,commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password']
        )
        profile= super().save(commit=False)
        profile.user=user
        if commit:
            profile.save()
        return profile
