# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import datetime
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


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
        ('student', 'นักศึกษา'),
        ('teacher', 'อาจารย์'),
        ('admin', 'ผู้ดูแลระบบ'),
    )

    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='student',
        verbose_name='ประเภทผู้ใช้'
    )

    student_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name='รหัสนักศึกษา'
    )

    year = models.IntegerField(
        choices=[
            (1, 'ชั้นปีที่ 1'),
            (2, 'ชั้นปีที่ 2'),
            (3, 'ชั้นปีที่ 3'),
            (4, 'ชั้นปีที่ 4'),
        ],
        null=True,
        blank=True,
        verbose_name='ชั้นปี'
    )

    branch = models.CharField(
        max_length=255,
        choices=BRANCH_CHOICES,
        null=True,
        blank=True,
        verbose_name='สาขา'
    )

    # กำหนด related_name ให้กับ groups และ user_permissions
    groups = models.ManyToManyField(
        Group,
        related_name="customuser_groups",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_permissions",
        blank=True
    )

    password_text = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name='รหัสผ่าน (ไม่เข้ารหัส)'
    )

    phone_number = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name="เบอร์โทรศัพท์"
    )

    class Meta:
        verbose_name = 'ผู้ใช้'
        verbose_name_plural = 'ผู้ใช้ทั้งหมด'

    def save(self, *args, **kwargs):
        if not self.pk:  # ถ้าเป็นการสร้างผู้ใช้ใหม่
            self.is_active = False  # ตั้งค่าเริ่มต้นให้บัญชีไม่สามารถใช้งานได้จนกว่าจะได้รับการอนุมัติ
            self.password_text = self._password  # เก็บรหัสผ่านก่อนการเข้ารหัส
        super().save(*args, **kwargs)


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

# โมเดลสำหรับการเข้าร่วมกิจกรรม
class Participation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'ยังไม่อนุมัติ'),
        ('approved', 'อนุมัติแล้ว'),
        ('rejected', 'ไม่อนุมัติ')  # เพิ่มสถานะใหม่
    ]
    
    activity = models.ForeignKey('Activity', on_delete=models.CASCADE, verbose_name='กิจกรรม')
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='นักศึกษา')
    joined_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='สถานะการลงทะเบียน'
    )
    joined_date = models.DateTimeField(auto_now_add=True, verbose_name="วันที่เข้าร่วม")

    class Meta:
        verbose_name = 'การเข้าร่วมกิจกรรม'
        verbose_name_plural = 'การเข้าร่วมกิจกรรมทั้งหมด'
        unique_together = ('activity', 'student')

    def __str__(self):
        return f"{self.student.username} เข้าร่วม {self.activity.name} - {self.get_status_display()}"



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
    # เพิ่มฟิลด์ faculty
    FACULTY_CHOICES = [
        ('all', 'ทุกคนเข้าร่วมได้'),
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
    faculty = models.CharField(
        max_length=10,
        choices=FACULTY_CHOICES,
        default='all',
        verbose_name='คณะที่จัดกิจกรรม'
    )
    max_participants = models.IntegerField(
        default=30, 
        verbose_name='จำนวนผู้เข้าร่วมสูงสุด'
    )

    def get_current_participants(self):
        """นับจำนวนผู้เข้าร่วมปัจจุบัน"""
        return self.participation_set.filter(status='approved').count()

    def is_full(self):
        """เช็คว่าเต็มหรือยัง"""
        return self.get_current_participants() >= self.max_participants

    def get_capacity_color(self):
        """กำหนดสีตามจำนวนผู้เข้าร่วม"""
        current = self.get_current_participants()
        if current >= self.max_participants:
            return 'bg-red-100'
        elif current >= (self.max_participants * 0.5):
            return 'bg-yellow-100'
        return 'bg-green-100'

    def get_participation_status(self, user):
        if not user.is_authenticated:
            return None
        participation = self.participation_set.filter(student=user).first()
        if not participation:
            return None
        if participation.status == 'pending':
            return "pending"
        return "approved" if participation.status == 'approved' else "rejected"

    def get_status_color(self, user):
        status = self.get_participation_status(user)
        if status == "pending":
            return "bg-yellow-50"
        elif status == "approved":
            return "bg-green-50"
        elif status == "rejected":
            return "bg-red-50"
        return "bg-white"

    @classmethod
    def get_unique_years(cls):
        """ดึงปีที่มีกิจกรรมทั้งหมด (ไม่ซ้ำกัน)"""
        from django.db.models.functions import ExtractYear
        return cls.objects.annotate(
            year=ExtractYear('start_date')
        ).values_list('year', flat=True).distinct().order_by('-year')

    @classmethod
    def get_unique_months(cls):
        """ดึงเดือนที่มีกิจกรรมทั้งหมด (ไม่ซ้ำกัน)"""
        from django.db.models.functions import ExtractMonth
        months = cls.objects.annotate(
            month=ExtractMonth('start_date')
        ).values_list('month', flat=True).distinct().order_by('month')
        
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        
        return [
            {
                'number': month,
                'name': thai_months.get(month, ''),
                'name_th': thai_months.get(month, '')
            }
            for month in months
        ]

    @staticmethod
    def get_thai_month_name(month_number):
        """แปลงเลขเดือนเป็นชื่อเดือนภาษาไทย"""
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        return thai_months.get(month_number, '')

    @classmethod
    def filter_by_month(cls, month):
        """กรองกิจกรรมตามเดือน"""
        return cls.objects.filter(start_date__month=month)

    @classmethod
    def filter_by_year(cls, year):
        """กรองกิจกรรมตามปี"""
        return cls.objects.filter(start_date__year=year)

    @classmethod
    def filter_by_month_year(cls, month, year):
        """กรองกิจกรรมตามเดือนและปี"""
        return cls.objects.filter(start_date__month=month, start_date__year=year)

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


class ActivityRegistration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    registration_date = models.DateTimeField(auto_now_add=True)
    proof_image = models.ImageField(upload_to='proof_images/', null=True, blank=True)
    proof_upload_date = models.DateTimeField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-registration_date']
        verbose_name = 'รูปหลักฐานการลงทะเบียนทั้งหมด'
        verbose_name_plural = 'รูปหลักฐานการลงทะเบียนทั้งหมด'
        unique_together = ['user', 'activity']  # ย้าย unique_together มาไว้ในที่เดียวกับการตั้งค่าอื่นๆ
    
    @property
    def has_proof(self):
        return bool(self.proof_image)

    def __str__(self):
        return f"{self.user.username} - {self.activity.name}"

    class Meta:
        ordering = ['-registration_date']
        verbose_name = 'รูปหลักฐานการลงทะเบียนทั้งหมด'
        verbose_name_plural = 'รูปหลักฐานการลงทะเบียนทั้งหมด'


class SystemLog(models.Model):
    # ตัวเลือกประเภทการกระทำ
    ACTION_CHOICES = [
        ('CREATE', 'สร้าง'),
        ('UPDATE', 'แก้ไข'),
        ('DELETE', 'ลบ'),
        ('LOGIN', 'เข้าสู่ระบบ'),
        ('LOGOUT', 'ออกจากระบบ'),
        ('APPROVE', 'อนุมัติ'),
        ('REJECT', 'ไม่อนุมัติ'),
        ('UPLOAD', 'อัพโหลดไฟล์'),
        ('DOWNLOAD', 'ดาวน์โหลดไฟล์'),
        ('OTHER', 'อื่นๆ'),
    ]

    # ฟิลด์พื้นฐาน
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='วันที่และเวลา')
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name='ผู้ใช้')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='การกระทำ')
    description = models.TextField(verbose_name='รายละเอียด')
    
    # ข้อมูลเพิ่มเติม
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP Address')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # ข้อมูลเพิ่มเติมสำหรับการวิเคราะห์
    user_agent = models.TextField(blank=True, null=True, verbose_name='User Agent')
    module = models.CharField(max_length=100, blank=True, verbose_name='โมดูล')
    status = models.CharField(max_length=50, blank=True, verbose_name='สถานะ')

    class Meta:
        verbose_name = 'บันทึกการใช้งานระบบ'
        verbose_name_plural = 'บันทึกการใช้งานระบบ'
        ordering = ['-timestamp']
