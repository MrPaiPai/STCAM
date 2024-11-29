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
    name = models.CharField(max_length=255)  # ชื่อกิจกรรม
    description = models.TextField()  # รายละเอียดกิจกรรม
    date = models.DateField()  # วันที่จัดกิจกรรม
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # ผู้สร้างกิจกรรม (admin)

    def __str__(self):
    return f"{self.student.username} - {self.activity.name}"  # ต้องเป็น string

# โมเดลสำหรับการเข้าร่วมกิจกรรม
class Participation(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)  # กิจกรรมที่เข้าร่วม
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # นักศึกษาที่เข้าร่วม
    participated = models.BooleanField(default=False)  # สถานะการเข้าร่วม (เข้าร่วมหรือไม่)

    def __str__(self):
        return f"{self.student.username} - {self.activity.name}"  # noqa

