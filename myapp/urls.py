from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # หน้าแรก
    path('register/', views.register, name='register'),  # ลงทะเบียน
    path('login/', views.login_view, name='login'),  # เข้าสู่ระบบ
    path('add-activity/', views.add_activity, name='add_activity'),  # เพิ่มกิจกรรม
    path('join-activity/<int:activity_id>/', views.join_activity, name='join_activity'),  # เข้าร่วมกิจกรรม
    path('activities/', views.activity_list, name='activity_list'),  # แสดงรายการกิจกรรมทั้งหมด
    path('participation-report/', views.participation_report, name='participation_report'),  # รายงานการเข้าร่วม
    # เส้นทางเพิ่มเติม
    path('my-activities/', views.my_activities, name='my_activities'),  # หน้ากิจกรรมที่ผู้ใช้เข้าร่วม
]
