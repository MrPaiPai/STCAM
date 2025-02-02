# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import datetime

BRANCH_CHOICES = [
    ('CS', 'วิทยาการคอมพิวเตอร์'),
    ('CCS', 'วิทยาศาสตร์เครื่องสำอาง'),
    ('OHS', 'อาชีวอนามัยและความปลอดภัย'),
    ('EHS', 'อนามัยสิ่งแวดล้อมและสาธารณภัย'),
    ('MS', 'วิทยาศาสตร์การแพทย์'),
    ('GS', 'วิทยาศาสตร์ทั่วไป'),
    ('IT', 'เทคโนโลยีสารสนเทศ'),
    ('BIB', 'อุตสาหกรรมชีวภาพเพื่อธุรกิจ'),
    ('CYB', 'ความมั่นคงปลอดภัยไซเบอร์'),
]

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
        verbose_name='ประเภทผู้ใช้'
    )
    year = models.IntegerField(
        choices=[
            (1, 'ชั้นปีที่ 1'),
            (2, 'ชั้นปีที่ 2'),
            (3, 'ชั้นปีที่ 3'),
            (4, 'ชั้นปีที่ 4'),
        ],
        null=True,  # อนุญาตให้เป็นค่าว่าง
        blank=True,
        verbose_name='ชั้นปี'
    )
    branch = models.CharField(
        max_length=255,
        choices=BRANCH_CHOICES,  # ใช้ตัวเลือกใหม่
        null=True,  # อนุญาตให้เป็นค่าว่าง
        blank=True,
        verbose_name='สาขา'
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
        verbose_name='ชื่อกิจกรรม'
    )
    description = models.TextField(
        verbose_name='รายละเอียดกิจกรรม'
    )
    start_date = models.DateField(
        verbose_name='วันที่เริ่มจัดกิจกรรม',
        default=datetime.date.today
    )
    end_date = models.DateField(
        verbose_name='วันที่สิ้นสุดกิจกรรม',
        null=True,  # ยอมให้เป็น NULL
        blank=True  # สามารถทิ้งว่างได้ในฟอร์ม
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='ผู้สร้างกิจกรรม'
    )

    class Meta:
        verbose_name = 'กิจกรรม'
        verbose_name_plural = 'กิจกรรมทั้งหมด'

    def __str__(self):
        return self.name

#โมเดลสำหรับการเพื่มประกาศที่หน้า home (index.html)
class Announcement(models.Model):
    title = models.CharField(max_length=200)  # หัวข้อประกาศ
    content = models.TextField()  # เนื้อหาประกาศ
    created_at = models.DateTimeField(auto_now_add=True)  # เวลาประกาศอัตโนมัติ

    def __str__(self):
        return self.title
