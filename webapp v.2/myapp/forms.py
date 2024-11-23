from django import forms
from .models import CustomUser

class StudentRegisterForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

class AdminRegisterForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'user_type']
        widgets = {
            'password': forms.PasswordInput(),
        }
