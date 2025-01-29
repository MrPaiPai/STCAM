from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='home'),  # หน้าแรก
    path('register/', views.register, name='register'),  # ลงทะเบียน
    path('login/', views.login_view, name='login'),  # เข้าสู่ระบบ
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('add-activity/', views.add_activity, name='add_activity'),  # เพิ่มกิจกรรม
    path('join-activity/<int:activity_id>/', views.join_activity, name='join_activity'),  # เข้าร่วมกิจกรรม
    path('activities/', views.activity_list, name='activity_list'),  # แสดงรายการกิจกรรมทั้งหมด
    path('participation-report/', views.participation_report, name='participation_report'),  # รายงานการเข้าร่วม
    path('edit_user/<int:user_id>/', views.edit_user, name='edit_user'),

    path('my-activities/', views.my_activities, name='my_activities'),  # หน้ากิจกรรมที่ผู้ใช้เข้าร่วม
    # path('menu/', views.menu, name='menu'),
    path('activity_info/', views.activity_info, name='activity_info'),
]

# เพิ่มบรรทัดนี้ใน urls.py เพื่อให้สามารถเข้าถึงไฟล์ที่อัปโหลด (เช่น รูปภาพ)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)