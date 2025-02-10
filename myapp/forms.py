from django import forms
from .models import CustomUser, Activity, ActivityImage
from .models import MyUser
from django.contrib.auth.forms import UserCreationForm
from .models import BRANCH_CHOICES
from django.contrib.auth.models import User


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
        user.set_password(self.cleaned_data["password1"])  # ตั้งค่ารหัสผ่าน
        user.student_id = self.cleaned_data["student_id"]  # บันทึกรหัสนักศึกษา
        user.branch = self.cleaned_data["branch"]  # บันทึกสาขา
        user.year = self.cleaned_data["year"]  # บันทึกชั้นปี
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

#เเก้ไขข้อมูลส่วนตัว
class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=True, label="ชื่อจริง")
    last_name = forms.CharField(max_length=100, required=True, label="นามสกุล")
    student_id = forms.CharField(max_length=20, required=True, label="รหัสนักศึกษา")

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'student_id']



class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']