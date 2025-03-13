from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import join_activity, get_participants, edit_profile, edit_userprofile
from myapp.views import manage_participation

urlpatterns = [
    path('', views.home, name='home'),  # หน้าแรก
    path('register/', views.register, name='register'),  # ลงทะเบียน
    path('login/', views.login_view, name='login'),  # เข้าสู่ระบบ
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('add-activity/', views.add_activity, name='add_activity'),  # เพิ่มกิจกรรม
    path('join-activity/<int:activity_id>/', views.join_activity, name='join_activity'),  # เข้าร่วมกิจกรรม
    path('activities/', views.activity_list, name='activity_list'),  # แสดงรายการกิจกรรมทั้งหมด
    path('participation-report/', views.participation_report, name='participation_report'),  # รายงานการเข้าร่วม
    path('edit_user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('my-activities/', views.my_activities, name='my_activities'),  # หน้ากิจกรรมที่ผู้ใช้เข้าร่วม
    path('activity_info/', views.activity_info, name='activity_info'),
    path('track-participation/', views.track_participation, name='track_participation'),
    path('upload-proof/', views.upload_proof, name='upload_proof'),
    path('activity/<int:activity_id>/', views.activity_info, name='activity_info'),  # เส้นทางไปยัง activity_info
    path('join-activity/<int:activity_id>/', join_activity, name='join_activity'),
    path('activity/<int:activity_id>/', views.activity_detail, name='activity_detail'),
    path('participants/<int:activity_id>/', get_participants, name='get_participants'),
    path("edit-profile/", edit_profile, name="edit_profile"),
    path('edit-userprofile/', views.edit_userprofile, name='edit_userprofile'),
    path('track-participation/', views.track_participation, name='track_participation'),
    path('update-participation-status/<int:participation_id>/', views.update_participation_status, name='update_participation_status'),
    path('upload-proof/', views.upload_proof, name='upload_proof'),
    path('proof-list/', views.user_upload_proof_list, name='user_upload_proof_list'),
    path('delete-proof/<int:reg_id>/', views.delete_proof, name='delete_proof'),
    path('show_all_proofs/', views.show_all_proofs, name='show_all_proofs'),
    path('manage-participation/<int:participation_id>/', views.manage_participation, name='manage_participation'),
    path('manage-participation/', views.manage_participation, name='manage_participation'),
    path('manage-participations/', views.manage_participations, name='manage_participations'),
    path('activity/<int:activity_id>/info/', views.activity_info, name='activity_info'),
]

# เพิ่มการเสิร์ฟไฟล์ media และ static ในโหมดพัฒนา
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)