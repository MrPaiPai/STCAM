from django.contrib import admin
from .models import CustomUser, Activity, Participation

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_type')
    list_filter = ('user_type',)

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'created_by')

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('activity', 'student', 'participated')
    list_filter = ('participated',)
