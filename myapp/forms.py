from django import forms
from .models import CustomUser, Activity, ActivityImage
from .models import MyUser
from django.contrib.auth.forms import UserCreationForm

# ฟอร์มสำหรับนักศึกษาลงทะเบียน
class StudentRegisterForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']  
        widgets = {
            'password': forms.PasswordInput(),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'student'  # ตั้งค่า user_type เป็น student
        if commit:
            user.save()
        return user

# ฟอร์มสำหรับแอดมินลงทะเบียน
class AdminRegisterForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'user_type']
        widgets = {
            'password': forms.PasswordInput(),
        }

# ฟอร์มสำหรับเพิ่มกิจกรรม
class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['name', 'description', 'date']

# ฟอร์มสำหรับอัปโหลดรูปภาพกิจกรรม
class ActivityImageForm(forms.ModelForm):
    class Meta:
        model = ActivityImage
        fields = ['image']

class MyUserForm(forms.ModelForm):
    class Meta:
        model = MyUser
        fields = ['username', 'email', 'role']  # กำหนดให้แสดงเฉพาะฟิลด์เหล่านี้

    # สามารถเพิ่มฟิลด์หรือการปรับแต่งเพิ่มเติมได้ เช่น ถ้าต้องการให้เลือก role เป็น dropdown
    role = forms.ChoiceField(choices=[('user', 'User'), ('teacher', 'Teacher')])

class MyUserCreationForm(UserCreationForm):
    class Meta:
        model = MyUser
        fields = ['username', 'email', 'role']

    role = forms.ChoiceField(choices=MyUser.ROLE_CHOICES, required=True)