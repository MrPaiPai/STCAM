from django import forms
from .models import CustomUser, Activity, ActivityImage
from .models import MyUser
from django.contrib.auth.forms import UserCreationForm
from .models import BRANCH_CHOICES

# ฟอร์มสำหรับนักศึกษาลงทะเบียน
class StudentRegisterForm(forms.ModelForm):
    branch = forms.ChoiceField(
        choices=BRANCH_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})  # ใช้ dropdown สำหรับสาขา
    )
    year = forms.ChoiceField(
        choices=[
            (1, 'ชั้นปีที่ 1'),
            (2, 'ชั้นปีที่ 2'),
            (3, 'ชั้นปีที่ 3'),
            (4, 'ชั้นปีที่ 4'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})  # ใช้ dropdown สำหรับชั้นปี
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'branch', 'year']  # ระบุฟิลด์ที่ต้องการใช้
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
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
        fields = ['username', 'email', 'password', 'branch', 'year', 'user_type']  # เพิ่ม branch และ year
        widgets = {
            'password': forms.PasswordInput(),
            'year': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
        }

# ฟอร์มสำหรับเพิ่มกิจกรรม
class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['name', 'description', 'start_date', 'end_date']

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

#เก็บสาขา กับ ชั้นปี
class RegisterForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    branch = forms.CharField(max_length=100)
    year = forms.ChoiceField(choices=[(1, 'ปี 1'), (2, 'ปี 2'), (3, 'ปี 3'), (4, 'ปี 4')])