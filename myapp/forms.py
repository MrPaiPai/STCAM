from django import forms
from .models import CustomUser, Activity, ActivityImage

# ฟอร์มสำหรับนักศึกษาลงทะเบียน
class StudentRegisterForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

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
        fields = ['name', 'description', 'date']  # ชื่อ, รายละเอียด, และวันที่ของกิจกรรม

# ฟอร์มสำหรับอัปโหลดรูปภาพกิจกรรม
class ActivityImageForm(forms.ModelForm):
    class Meta:
        model = ActivityImage
        fields = ['image']  # ฟิลด์สำหรับรูปภาพ
