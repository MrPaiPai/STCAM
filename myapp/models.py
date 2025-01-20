# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

# โมเดลสำหรับ Custom User
class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'นักศึกษา'),  # นักศึกษา
        ('teacher', 'อาจารย์'),   # อาจารย์
        ('admin', 'ผู้ดูแลระบบ'),  # ผู้ดูแลระบบ
    )
    user_type = models.CharField(
        max_length=10, 
        choices=USER_TYPE_CHOICES, 
        default='student',
        verbose_name='ประเภทผู้ใช้'  # กำหนดคำอธิบายเป็นภาษาไทย
    )

    # กำหนด related_name ให้กับ groups และ user_permissions
    groups = models.ManyToManyField(
        Group, 
        related_name="customuser_groups",  # กำหนดชื่อที่ไม่ซ้ำกัน
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission, 
        related_name="customuser_permissions",  # กำหนดชื่อที่ไม่ซ้ำกัน
        blank=True
    )

    class Meta:
        verbose_name = 'ผู้ใช้'
        verbose_name_plural = 'ผู้ใช้ทั้งหมด'


# โมเดลสำหรับ MyUser
class MyUser(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('teacher', 'Teacher'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    # กำหนด related_name ให้กับ groups และ user_permissions
    groups = models.ManyToManyField(
        Group, 
        related_name="myuser_groups",  # กำหนดชื่อที่ไม่ซ้ำกัน
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission, 
        related_name="myuser_permissions",  # กำหนดชื่อที่ไม่ซ้ำกัน
        blank=True
    )
    
    def __str__(self):
        return self.username

# โมเดลสำหรับรูปภาพกิจกรรม
class ActivityImage(models.Model):
    activity = models.ForeignKey(
        'Activity',  # ใช้ 'Activity' ในการอ้างอิงโมเดล Activity
        on_delete=models.CASCADE,
        related_name='images',  # ใช้ related_name เพื่อเข้าถึงรูปภาพของกิจกรรมได้ง่าย
        verbose_name='กิจกรรม'  # กิจกรรมที่มีรูปภาพ
    )
    image = models.ImageField(
        upload_to='activity_images/', 
        verbose_name='รูปภาพ'  # อัปโหลดไปที่โฟลเดอร์ activity_images/
    )

    class Meta:
        verbose_name = 'รูปภาพกิจกรรม'
        verbose_name_plural = 'รูปภาพทั้งหมด'

    def __str__(self):
        return f"รูปภาพสำหรับ {self.activity.name}"

## โมเดลสำหรับการเข้าร่วมกิจกรรม
class Participation(models.Model):
    activity = models.ForeignKey(
        'Activity',  
        on_delete=models.CASCADE, 
        verbose_name='กิจกรรม'  # กิจกรรมที่เข้าร่วม
    )
    student = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        verbose_name='นักศึกษา'  # นักศึกษาที่เข้าร่วม
    )
    participated = models.BooleanField(
        default=False, 
        verbose_name='สถานะการเข้าร่วม'  # สถานะการเข้าร่วม (เข้าร่วมหรือไม่)
    )

    class Meta:
        verbose_name = 'การเข้าร่วมกิจกรรม'
        verbose_name_plural = 'การเข้าร่วมกิจกรรมทั้งหมด'

    def __str__(self):
        return f"{self.student.username} - {self.activity.name}"


# โมเดลสำหรับกิจกรรม
class Activity(models.Model):
    name = models.CharField(
        max_length=255, 
        verbose_name='ชื่อกิจกรรม'  # ชื่อกิจกรรม
    )
    description = models.TextField(
        verbose_name='รายละเอียดกิจกรรม'  # รายละเอียดกิจกรรม
    )
    date = models.DateField(
        verbose_name='วันที่จัดกิจกรรม'  # วันที่จัดกิจกรรม
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='ผู้สร้างกิจกรรม'  # ผู้สร้างกิจกรรม
    )

    class Meta:
        verbose_name = 'กิจกรรม'
        verbose_name_plural = 'กิจกรรมทั้งหมด'

    def __str__(self):
        return self.name
