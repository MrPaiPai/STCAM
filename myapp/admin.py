from django.contrib import admin
from .models import CustomUser, Activity, Participation, ActivityImage
from django.contrib.auth.admin import UserAdmin
from .models import MyUser
from .forms import MyUserForm
from myapp.models import CustomUser  
from .models import Announcement


# Inline class สำหรับจัดการรูปภาพในหน้ากิจกรรม
class ActivityImageInline(admin.TabularInline):
    model = ActivityImage
    extra = 1  # เพิ่มช่องสำหรับอัปโหลดรูปภาพใหม่ 1 ช่อง
    verbose_name = 'รูปภาพ'
    verbose_name_plural = 'รูปภาพทั้งหมด'

# การจัดการ CustomUser
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = MyUserForm  # ถ้าต้องการใช้ฟอร์มที่กำหนดเอง
    model = CustomUser
    list_display = ('username', 'email', 'user_type', 'year', 'branch', 'is_active', 'is_staff')  # เพิ่ม field ใหม่
    list_filter = ('user_type', 'year', 'branch', 'is_active', 'is_staff')  # เพิ่มตัวกรองชั้นปีและสาขา
    search_fields = ('username', 'email', 'year', 'branch')  # สามารถค้นหาตามชั้นปีและสาขา

    # การจัดการฟอร์มการเพิ่มผู้ใช้
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type', 'year', 'branch'),
        }),
    )

    # การจัดการฟอร์มการแก้ไขผู้ใช้
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password', 'user_type', 'year', 'branch', 'is_active', 'is_staff', 'groups', 'user_permissions'),
        }),
    )

    # แสดงผลตามประเภทผู้ใช้
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

# การจัดการ Activity พร้อม Inline สำหรับรูปภาพ
@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'created_by')
    list_filter = ('start_date', 'end_date', 'created_by')
    inlines = [ActivityImageInline]

    # จำกัดการแสดงผลตามประเภทผู้ใช้
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.user_type == 'teacher':  # ถ้าเป็นอาจารย์
            return queryset.filter(created_by=request.user)
        return queryset  # แสดงข้อมูลทั้งหมดสำหรับ admin

    def has_change_permission(self, request, obj=None):
        if request.user.user_type == 'teacher' and obj:
            return obj.created_by == request.user  # อนุญาตเฉพาะกิจกรรมที่สร้างโดยอาจารย์นั้น
        return super().has_change_permission(request, obj)

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('activity', 'student', 'participated')
    list_filter = ('participated', 'activity')  # เพิ่มตัวกรองตามกิจกรรม

    # จำกัดการแสดงผลตามประเภทผู้ใช้
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.user_type == 'teacher':
            return queryset.filter(activity__created_by=request.user)
        return queryset

class MyUserAdmin(UserAdmin):
    form = MyUserForm
    model = MyUser
    list_display = ['username', 'email', 'role']
    list_filter = ['role']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )

admin.site.register(MyUser, MyUserAdmin)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'content')