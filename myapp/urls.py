from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import join_activity
from .views import get_participants
from .views import edit_profile
from .views import edit_userprofile

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
    path('track-participation/', views.track_participation, name='track_participation'),
    path('upload-proof/', views.upload_proof, name='upload_proof'),
    path('add_announcement/', views.add_announcement, name='add_announcement'),
    path('activity/<int:activity_id>/', views.activity_info, name='activity_info'),  # เส้นทางไปยัง activity_info
    path('join-activity/<int:activity_id>/', join_activity, name='join_activity'),
    path('activity/<int:activity_id>/', views.activity_detail, name='activity_detail'),
    path('participants/<int:activity_id>/', get_participants, name='get_participants'),
    path("edit-profile/", edit_profile, name="edit_profile"),
    path('edit-userprofile/', views.edit_userprofile, name='edit_userprofile'),
    path('track-participation/', views.track_participation, name='track_participation'),
    path('update-participation-status/<int:participation_id>/',views.update_participation_status, name='update_participation_status'),
    path('upload-proof/', views.upload_proof, name='upload_proof'),
    path('proof-list/', views.user_upload_proof_list, name='user_upload_proof_list'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# เพิ่มบรรทัดนี้ใน urls.py เพื่อให้สามารถเข้าถึงไฟล์ที่อัปโหลด (เช่น รูปภาพ)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)