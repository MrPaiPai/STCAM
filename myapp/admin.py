from django.contrib import admin
from .models import CustomUser, Activity, Participation, ActivityImage
from django.contrib.auth.admin import UserAdmin
from .models import MyUser
from .forms import MyUserForm
from myapp.models import CustomUser  
from .models import Announcement
from django.utils.html import format_html
from .models import ActivityRegistration

# Inline class สำหรับจัดการรูปภาพในหน้ากิจกรรม
class ActivityImageInline(admin.TabularInline):
    model = ActivityImage
    extra = 1  # เพิ่มช่องสำหรับอัปโหลดรูปภาพใหม่ 1 ช่อง
    verbose_name = 'รูปภาพ'
    verbose_name_plural = 'รูปภาพทั้งหมด'

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # แสดงฟิลด์เพิ่มเติมในหน้ารายการผู้ใช้
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'student_id', 'year', 'branch', 'is_active', 'is_staff')
    list_filter = ('user_type', 'year', 'branch', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'student_id', 'year', 'branch')

    # ฟอร์มเพิ่มผู้ใช้ใหม่
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'user_type', 'student_id', 'year', 'branch'),
        }),
    )

    # ฟอร์มแก้ไขผู้ใช้
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'first_name', 'last_name', 'password', 'user_type', 'student_id', 'year', 'branch', 'is_active', 'is_staff', 'groups', 'user_permissions'),
        }),
    )

    # แสดงผลตามประเภทผู้ใช้
    def get_queryset(self, request):
        return super().get_queryset(request)


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



# เช็คก่อนว่า Participation ถูก register ไปแล้วหรือยัง
if admin.site.is_registered(Participation):
    admin.site.unregister(Participation)

# @admin.register(Participation)
# class ParticipationAdmin(admin.ModelAdmin):
#     list_display = ('activity', 'student', 'participated')  # ใช้ method แทน field
#     list_filter = ('activity',)  # ลบ 'participated'
#     search_fields = ('student__username', 'activity__name')
#     ordering = ('activity', 'student')

#     def participated(self, obj):
#         return True  # หรือใช้เงื่อนไขที่เหมาะสม เช่น obj.date_joined ไม่เป็น null
#     participated.short_description = "เข้าร่วมแล้ว"  # เปลี่ยนชื่อคอลัมน์ใน Django Admin

#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         if hasattr(request.user, 'user_type') and request.user.user_type == 'teacher':
#             return queryset.filter(activity__created_by=request.user)
#         return queryset

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


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ['student', 'activity', 'joined_at', 'status_badge', 'get_branch', 'get_year', 'participated']
    list_filter = ['status', 'activity', 'student__branch', 'student__year']
    search_fields = ['student__username', 'student__first_name', 'activity__name']
    ordering = ('activity', 'student')
    actions = ['approve_participations', 'reject_participations']
    
    def get_branch(self, obj):
        return obj.student.get_branch_display()
    get_branch.short_description = 'สาขา'
    
    def get_year(self, obj):
        return f"ชั้นปีที่ {obj.student.year}"
    get_year.short_description = 'ชั้นปี'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger'
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            {'warning': '#ffc107', 'success': '#28a745', 'danger': '#dc3545'}[colors[obj.status]],
            obj.get_status_display()
        )
    status_badge.short_description = 'สถานะ'

    def participated(self, obj):
        return True  # หรือใช้เงื่อนไขที่เหมาะสม
    participated.short_description = "เข้าร่วมแล้ว"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if hasattr(request.user, 'user_type') and request.user.user_type == 'teacher':
            return queryset.filter(activity__created_by=request.user)
        return queryset

    @admin.action(description='อนุมัติการเข้าร่วมที่เลือก')
    def approve_participations(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'อนุมัติการเข้าร่วมจำนวน {updated} รายการ')

    @admin.action(description='ไม่อนุมัติการเข้าร่วมที่เลือก')
    def reject_participations(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'ไม่อนุมัติการเข้าร่วมจำนวน {updated} รายการ')


class ActivityRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'proof_image', 'proof_upload_date')
    list_filter = ('activity', 'proof_upload_date')
    search_fields = ('user__username', 'activity__name')

admin.site.register(ActivityRegistration, ActivityRegistrationAdmin)



