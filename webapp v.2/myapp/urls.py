from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('add-activity/', views.add_activity, name='add_activity'),
    path('participation-report/', views.participation_report, name='participation_report'),
]
