from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import StudentRegisterForm, AdminRegisterForm, ActivityForm, ActivityImageForm
from .models import Activity, ActivityImage, Participation
from django.forms import modelformset_factory
from .models import MyUser
from .forms import MyUserForm
from django.urls import reverse
from .models import Announcement
from django.views.decorators.csrf import csrf_exempt  # ใช้ในกรณีที่ไม่ต้องการ CSRF error
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from .forms import ProfileEditForm
from .forms import UserProfileForm
from .models import ActivityRegistration
from django.utils import timezone
from .models import CustomUser
from .models import BRANCH_CHOICES
from datetime import datetime
from django.db.models import Prefetch
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from io import BytesIO
import os
from .utils import create_log
from django.db.models.functions import ExtractYear, ExtractMonth

# views.py

def some_view(request):
    return redirect(reverse('home'))  # ใช้ชื่อ URL 'home' ที่กำหนดใน urls.py

# ฟังก์ชันตรวจสอบว่าเป็นนศหรือไม่
def is_student(user):
    return user.user_type == 'student'

# ฟังก์ชันตรวจสอบว่าเป็นอาจารย์หรือไม่
def is_teacher(user):
    return user.user_type == 'teacher' or (hasattr(user, 'role') and user.role == 'teacher')

# ฟังก์ชันตรวจสอบว่าเป็น admin หรือไม่
def is_admin(user):
    return user.user_type == 'admin'

# ฟังก์ชันสำหรับหน้าแรก
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)

# ฟังก์ชันสำหรับการลงทะเบียนผู้ใช้
def register(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'student'  # กำหนดประเภทเป็น student
            user.is_active = True  # ✅ ตั้งค่าให้ user สามารถใช้งานได้ทันที
            user.save()

            # ทำการ login หลังจากลงทะเบียนสำเร็จ
            user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password1'])
            if user:
                login(request, user)
                messages.success(request, 'ลงทะเบียนสำเร็จ! ยินดีต้อนรับเข้าสู่ระบบ')  # ✅ เพิ่มข้อความสำเร็จ
                return redirect('home')  # เปลี่ยนให้ไปที่หน้า home หลังจาก login สำเร็จ
    else:
        form = StudentRegisterForm()
    return render(request, 'register.html', {'form': form})



@login_required
def edit_profile(request):
    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("home")  # ✅ กลับไปหน้าแรกหลังจากแก้ไขสำเร็จ
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, "edit_profile.html", {"form": form})



# ฟังก์ชันสำหรับการเข้าสู่ระบบ
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')  # ✅ ใช้ get() เพื่อป้องกัน KeyError
        password = request.POST.get('password')
        
        if username and password:  # ✅ ตรวจสอบว่ามีการกรอกข้อมูลครบ
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('home')
                else:
                    messages.error(request, "บัญชีผู้ใช้นี้ถูกปิดการใช้งาน")
            else:
                messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        else:
            messages.error(request, "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
    
    return render(request, 'login.html')


# ฟังก์ชันสำหรับ admin เพิ่มกิจกรรม
@user_passes_test(is_admin)
def add_activity(request):
    ImageFormSet = modelformset_factory(ActivityImage, form=ActivityImageForm, extra=3)
    if request.method == 'POST':
        activity_form = ActivityForm(request.POST)
        formset = ImageFormSet(request.POST, request.FILES, queryset=ActivityImage.objects.none())
        if activity_form.is_valid() and formset.is_valid():
            activity = activity_form.save(commit=False)
            activity.created_by = request.user
            activity.save()

            for form in formset.cleaned_data:
                if form:
                    image = form['image']
                    ActivityImage.objects.create(activity=activity, image=image)

            return redirect('home')
    else:
        activity_form = ActivityForm()
        formset = ImageFormSet(queryset=ActivityImage.objects.none())
    return render(request, 'add_activity.html', {'activity_form': activity_form, 'formset': formset})

# ฟังก์ชันสำหรับนักเรียนเข้าร่วมกิจกรรม
@login_required
def join_activity(request, activity_id):
    if request.method == 'POST':
        activity = get_object_or_404(Activity, id=activity_id)
        
        # ตรวจสอบว่าผู้ใช้เคยเข้าร่วมกิจกรรมนี้แล้วหรือไม่
        participation, created = Participation.objects.get_or_create(
            activity=activity,
            student=request.user
        )

        if created:
            # ถ้าเป็นการลงทะเบียนใหม่
            return JsonResponse({
                'status': 'success',
                'message': 'ลงทะเบียนสำเร็จ กรุณารอการอนุมัติ'
            })
        else:
            # ถ้าเคยลงทะเบียนแล้ว
            return JsonResponse({
                'status': 'error',
                'message': 'คุณเคยลงทะเบียนกิจกรรมนี้แล้ว'
            })
    
    # ถ้าไม่ใช่ POST request
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

# ฟังก์ชันแสดงรายการกิจกรรมทั้งหมด
@login_required
def activity_list(request):
    # เก็บโค้ดเดิมไว้ทั้งหมด
    activities = Activity.objects.all()
    
    # Get filter parameters (โค้ดเดิม)
    year = request.GET.get('year')
    month = request.GET.get('month')
    day = request.GET.get('day')
    
    # Apply filters to start_date (โค้ดเดิม)
    if year:
        activities = activities.filter(start_date__year=year)
    if month:
        activities = activities.filter(start_date__month=month)
    if day:
        activities = activities.filter(start_date__day=day)

    # Generate choices for filters (โค้ดเดิม)
    current_year = datetime.now().year
    years = range(current_year - 2, current_year + 2)
    
    months = [
        (1, 'มกราคม'), (2, 'กุมภาพันธ์'), (3, 'มีนาคม'),
        (4, 'เมษายน'), (5, 'พฤษภาคม'), (6, 'มิถุนายน'),
        (7, 'กรกฎาคม'), (8, 'สิงหาคม'), (9, 'กันยายน'),
        (10, 'ตุลาคม'), (11, 'พฤศจิกายน'), (12, 'ธันวาคม')
    ]
    
    days = range(1, 32)

    # เพิ่มโค้ดใหม่สำหรับการดึงข้อมูลเดือนและปีที่มีกิจกรรม
    available_months = Activity.get_unique_months()
    available_years = Activity.get_unique_years()

    # สร้าง context โดยรวมทั้งข้อมูลเดิมและข้อมูลใหม่
    context = {
        'activities': activities,
        'years': years,
        'months': months,
        'days': days,
        'selected_year': year,
        'selected_month': month,
        'selected_day': day,
        # เพิ่มข้อมูลใหม่
        'available_months': available_months,
        'available_years': available_years
    }
    
    return render(request, 'activity_list.html', context)

# ฟังก์ชันแสดงรายงานการเข้าร่วมกิจกรรม
@user_passes_test(is_admin)
def participation_report(request):
    participations = Participation.objects.select_related('activity', 'student')
    return render(request, 'participation_report.html', {'participations': participations})

# ฟังก์ชันแสดงกิจกรรมที่ผู้ใช้เข้าร่วม
@login_required
def my_activities(request):
    activities = Participation.objects.filter(student=request.user)
    return render(request, 'my_activities.html', {'activities': activities})

# ตรวจสอบว่า user เป็น teacher หรือไม่
def is_teacher(user):
    return user.role == 'teacher'

@user_passes_test(is_teacher)
def teacher_view(request):
    return render(request, 'teacher_dashboard.html')

def edit_user(request, user_id):
    user = get_object_or_404(MyUser, pk=user_id)  # ค้นหาผู้ใช้จาก ID
    if request.method == 'POST':
        form = MyUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()  # บันทึกการเปลี่ยนแปลง
            return redirect('admin:myuser_changelist')  # เปลี่ยนเส้นทางไปที่หน้า User List ใน Admin
    else:
        form = MyUserForm(instance=user)  # โหลดข้อมูลของผู้ใช้ในฟอร์ม
    return render(request, 'myapp/user_form.html', {'form': form})

#ติดตามสถานนะการลงทะเบียน
@login_required
def track_participation(request):
    # ดึงเฉพาะกิจกรรมที่ user เข้าร่วม
    participations = Participation.objects.filter(student=request.user).select_related('activity')
    participation = participations.first()  # ดึงแค่ตัวแรก ถ้ามี

    context = {
        'participations': participations,
        'participation': participation,  # ส่งตัวเดียวไปด้วย
    }
    return render(request, 'track_participation.html', context)

#อัพเดจสถานนะการลงทะเบียน
@login_required
def update_participation_status(request, participation_id):
    if request.method == 'POST':
        participation = get_object_or_404(Participation, id=participation_id)
        try:
            # ดึงข้อมูลจาก JSON body
            import json
            data = json.loads(request.body.decode('utf-8'))
            new_status = data.get('status')
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error decoding JSON: {e}")
            return JsonResponse({'status': 'error', 'message': 'ข้อมูลที่ส่งมาไม่ถูกต้อง'}, status=400)

        print(f"Received request to update participation {participation_id} to {new_status}")
        if new_status in ['approved', 'rejected']:
            participation.status = new_status
            participation.save()
            print(f"Updated participation {participation_id} to {new_status}")
            return JsonResponse({
                'status': 'success',
                'new_status': new_status
            })
        print(f"Invalid status: {new_status}")
        return JsonResponse({'status': 'error', 'message': 'สถานะไม่ถูกต้อง'}, status=400)
    print("Method not allowed")
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 
                "full_name": f"{p.student.first_name} {p.student.last_name}",
                "year": p.student.year,  
                "branch": p.student.get_branch_display(),
                "joined_at": p.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for p in participants
        ]
        return JsonResponse({"participants": data})
    except Activity.DoesNotExist:
        return JsonResponse({"error": "กิจกรรมไม่พบ"}, status=404)


#ไปยังหน้าเเก้ไขข้อมูลส่วนตัว
@login_required
def edit_userprofile(request):
    user = request.user
    
    # ดึงค่า filter จาก request
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วมพร้อมกับข้อมูลสถานะ
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')  # เพิ่ม select_related เพื่อลดจำนวน queries
    
    # นำ filter มาใช้
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    
    # สร้าง list เก็บข้อมูลกิจกรรมพร้อมสถานะ
    activities_with_status = []
    for p in participations:
        activities_with_status.append({
            'activity': p.activity,
            'status': p.status,
            'joined_at': p.joined_at
        })
    
    # ดึงรายการเดือนและปีที่มีกิจกรรม
    available_months = []
    available_years = []
    
    if participations.exists():
        # ดึงปีที่มีกิจกรรม
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
        # ดึงเดือนที่มีกิจกรรม
        months = participations.dates('activity__start_date', 'month')
        thai_months = {
            1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม',
            4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน',
            7: 'กรกฎาคม', 8: 'สิงหาคม', 9: 'กันยายน',
            10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'
        }
        available_months = [
            {'number': month.month, 'name_th': thai_months[month.month]}
            for month in months
        ]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'อัพเดทข้อมูลสำเร็จ')
            return redirect('edit_userprofile')
    else:
        form = UserProfileForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_status,  # ส่งข้อมูลกิจกรรมพร้อมสถานะ
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)


# อัพโหลดหลักฐานการเข้าร่วม
@login_required
@csrf_exempt  # เพิ่มเพื่อให้แน่ใจว่าไม่มีปัญหา CSRF (ถ้าไม่ใช้ก็ลบได้)
def upload_proof(request):
    # ดึงพารามิเตอร์สำหรับ filter
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้เข้าร่วมและได้รับการอนุมัติ
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # ดึงข้อมูลการลงทะเบียนที่มีอยู่แล้ว
    existing_registrations = ActivityRegistration.objects.filter(
        user=request.user,
        proof_image__isnull=False  # เฉพาะที่มีรูปภาพ
    ).values_list('activity_id', flat=True)

    # กรองเฉพาะกิจกรรมที่ยังไม่ได้อัพโหลดหลักฐาน
    participations = participations.exclude(
        activity_id__in=existing_registrations
    )

    # ใช้ filters
    if activity_filter:
        participations = participations.filter(activity_id=activity_filter)
    if date_filter:
        participations = participations.filter(joined_at__date=date_filter)
    if month_filter:
        participations = participations.filter(joined_at__month=month_filter)
    if year_filter:
        participations = participations.filter(joined_at__year=year_filter)

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
            proof_image = request.FILES.get('proof_image')

            if not activity_id or not proof_image:
                return JsonResponse({
                    'success': False,
                    'error': 'กรุณาระบุรหัสกิจกรรมและเลือกรูปภาพ'
                })

            activity = get_object_or_404(Activity, id=activity_id)
            
            # สร้างหรืออัพเดตข้อมูลการลงทะเบียน
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'status': 'pending'
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M")
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ดึงข้อมูลสำหรับ filters
    available_months = participations.dates('joined_at', 'month')
    available_years = participations.dates('joined_at', 'year')

    context = {
        'participations': participations,
        'months': [{'number': d.month, 'name': d.strftime('%B')} for d in available_months],
        'years': [d.year for d in available_years],
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)
def index(request):
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.all()
    
    if filter_type == 'upcoming':
        # แสดงกิจกรรมที่ยังไม่หมดเวลา
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type == 'pending' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='pending'
        ).distinct()
    elif filter_type == 'approved' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='approved'
        ).distinct()
    elif filter_type == 'rejected' and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status='rejected'
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # ส่งวันที่ปัจจุบันไปให้ template
    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''

    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            # แก้จาก is_approved เป็น status
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"

    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color
    })

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login



def activity_detail(request, activity_id):
    # ดึงข้อมูลกิจกรรมจากฐานข้อมูลโดยใช้ activity_id
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ส่งข้อมูลกิจกรรมไปยังเทมเพลต
    context = {
        'activity': activity,
    }
    
    # เรนเดอร์เทมเพลตและส่ง context ไปด้วย
    return render(request, 'myapp/activity_detail.html', context)


def get_participants(request, activity_id):
    try:
        activity = get_object_or_404(Activity, id=activity_id)
        participants = Participation.objects.filter(activity=activity)
        data = [
            {
                "username": p.student.username, 