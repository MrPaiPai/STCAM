# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

# โมเดลสำหรับ Custom User
class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),  # นักศึกษา
        ('admin', 'Admin'),      # ผู้ดูแลระบบ
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')  # กำหนดประเภทผู้ใช้

# โมเดลสำหรับกิจกรรม
class Activity(models.Model):
    name = models.CharField(max_length=255, verbose_name='ชื่อกิจกรรม')  # ชื่อกิจกรรม
    description = models.TextField(verbose_name='รายละเอียดกิจกรรม')  # รายละเอียดกิจกรรม
    date = models.DateField(verbose_name='วันที่จัดกิจกรรม')  # วันที่จัดกิจกรรม
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='ผู้สร้างกิจกรรม'
    )

    class Meta:
        verbose_name = 'กิจกรรม'
        verbose_name_plural = 'กิจกรรมทั้งหมด'

    def __str__(self):  # ฟังก์ชันแสดงผลของโมเดล
        return self.name

# โมเดลสำหรับการเข้าร่วมกิจกรรม
class Participation(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, verbose_name='กิจกรรม')  # กิจกรรมที่เข้าร่วม
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='นักศึกษา')  # นักศึกษาที่เข้าร่วม
    participated = models.BooleanField(default=False, verbose_name='สถานะการเข้าร่วม')  # สถานะการเข้าร่วม (เข้าร่วมหรือไม่)

    def __str__(self):  # ฟังก์ชันแสดงผลของโมเดล
        return f"{self.student.username} - {self.activity.name}"  # ต้องเป็น string

# โมเดลสำหรับรูปภาพกิจกรรม
class ActivityImage(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='images',  # ใช้ related_name เพื่อเข้าถึงรูปภาพของกิจกรรมได้ง่าย
        verbose_name='กิจกรรม'
    )
    image = models.ImageField(upload_to='activity_images/', verbose_name='รูปภาพ')  # อัปโหลดไปที่โฟลเดอร์ activity_images/

    class Meta:
        verbose_name = 'รูปภาพกิจกรรม'
        verbose_name_plural = 'รูปภาพทั้งหมด'

    def __str__(self):  # ฟังก์ชันแสดงผลของโมเดล
        return f"รูปภาพสำหรับ {self.activity.name}"
