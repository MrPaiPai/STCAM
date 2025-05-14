from django import forms
from .models import CustomUser, Activity, ActivityImage
from .models import MyUser
from django.contrib.auth.forms import UserCreationForm
from .models import BRANCH_CHOICES
from django.contrib.auth.models import User
from django.contrib.admin.widgets import AdminDateWidget

# ฟอร์มสำหรับนักศึกษาลงทะเบียน
class StudentRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True, label="ชื่อจริง")
    last_name = forms.CharField(max_length=100, required=True, label="นามสกุล")
    student_id = forms.CharField(max_length=20, required=True, label="รหัสนักศึกษา")
    branch = forms.ChoiceField(
        choices=BRANCH_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="สาขา"
    )
    year = forms.ChoiceField(
        choices=[(1, 'ชั้นปีที่ 1'), (2, 'ชั้นปีที่ 2'), (3, 'ชั้นปีที่ 3'), (4, 'ชั้นปีที่ 4')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="ชั้นปี"
    )
    password1 = forms.CharField(widget=forms.PasswordInput, required=True, label="รหัสผ่าน")
    password2 = forms.CharField(widget=forms.PasswordInput, required=True, label="ยืนยันรหัสผ่าน")

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'student_id', 'branch', 'year']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.password_text = self.cleaned_data["password1"]  # เพิ่มบรรทัดนี้
        user.student_id = self.cleaned_data["student_id"]
        user.branch = self.cleaned_data["branch"]
        user.year = self.cleaned_data["year"]
        user.user_type = 'student'
        if commit:
            user.save()
        return user

# ฟอร์มสำหรับแอดมินลงทะเบียน
class AdminRegisterForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'branch', 'year', 'user_type']
        widgets = {
            'password': forms.PasswordInput(),
            'year': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
        }

# ฟอร์มสำหรับเพิ่มกิจกรรม
class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        # แก้ไขฟิลด์ให้ตรงกับที่มีในโมเดล Activity จริงๆ
        fields = ['name', 'description', 'start_date', 'end_date', 'faculty', 'max_participants']
        widgets = {
            'start_date': AdminDateWidget(),
            'end_date': AdminDateWidget(),
            'faculty': forms.Select(attrs={'class': 'form-control'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'กำหนด 0 หากไม่จำกัดจำนวน'}),
        }
        labels = {
            'name': 'ชื่อกิจกรรม',
            'description': 'รายละเอียด',
            'start_date': 'วันที่เริ่ม',
            'end_date': 'วันที่สิ้นสุด',
            'faculty': 'คณะที่จัดกิจกรรม',
            'max_participants': 'จำนวนผู้เข้าร่วมสูงสุด',
        }
    
    # เพิ่มเมธอดนี้เพื่อกำหนดว่าฟิลด์ใดไม่จำเป็นต้องกรอกในโหมดแก้ไข
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ถ้าเป็นการแก้ไขข้อมูลที่มีอยู่แล้ว (instance มีค่า)
        if self.instance.pk:
            # ทำให้ฟิลด์เหล่านี้ไม่จำเป็น
            self.fields['description'].required = False

# ฟอร์มสำหรับอัปโหลดรูปภาพกิจกรรม
class ActivityImageForm(forms.ModelForm):
    class Meta:
        model = ActivityImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ทำให้ฟิลด์รูปภาพไม่จำเป็นในกรณีของการแก้ไข
        # เพื่อป้องกันปัญหา "This field is required"
        if self.instance and self.instance.pk:
            self.fields['image'].required = False

class MyUserForm(forms.ModelForm):
    class Meta:
        model = MyUser
        fields = ['username', 'email', 'role']
    role = forms.ChoiceField(choices=[('user', 'User'), ('teacher', 'Teacher')])

class MyUserCreationForm(UserCreationForm):
    class Meta:
        model = MyUser
        fields = ['username', 'email', 'role']
    role = forms.ChoiceField(choices=MyUser.ROLE_CHOICES, required=True)

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    branch = forms.CharField(max_length=100)
    year = forms.ChoiceField(choices=[(1, 'ปี 1'), (2, 'ปี 2'), (3, 'ปี 3'), (4, 'ปี 4')])

class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=True, label="ชื่อจริง")
    last_name = forms.CharField(max_length=100, required=True, label="นามสกุล")
    student_id = forms.CharField(max_length=20, required=True, label="รหัสนักศึกษา")

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'student_id']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser  # เปลี่ยนจาก MyUser เป็น CustomUser
        fields = ['first_name', 'last_name', 'email', 'student_id']  # เอา phone_number ออกถ้าไม่มีฟิลด์นี้
        labels = {
            'first_name': 'ชื่อ',
            'last_name': 'นามสกุล',
            'email': 'อีเมล',
            'student_id': 'รหัสนักศึกษา',
        }

class StaffRegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("รหัสผ่านไม่ตรงกัน")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data["password1"]
        user.set_password(password)
        user.password_text = password  # เพิ่มบรรทัดนี้
        if commit:
            user.save()
        return user