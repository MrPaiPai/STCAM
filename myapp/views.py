from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_protect  # เอา csrf_exempt ออกเพื่อความปลอดภัย
from django.http import JsonResponse, HttpResponse  # เพิ่ม HttpResponse ตรงนี้
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.forms import modelformset_factory
from django.forms.models import inlineformset_factory  # เพิ่มบรรทัดนี้
from django.db.models import Prefetch
from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required
import json
from .models import MyUser, Activity, ActivityRegistration, Participation
from .forms import AdminRegisterForm


# นำเข้า forms ที่จำเป็น
from .forms import (
    StudentRegisterForm, AdminRegisterForm, ActivityForm,
    ActivityImageForm, MyUserForm, ProfileEditForm, UserProfileForm
)

# นำเข้า models ที่จำเป็น
from .models import (
    Activity, ActivityImage, Participation,
    Announcement, ActivityRegistration, CustomUser, MyUser
)

# ฟังก์ชันตรวจสอบสิทธิ์
def is_student(user):
    """ตรวจสอบว่าผู้ใช้เป็นนักศึกษาหรือไม่"""
    return hasattr(user, 'role') and user.role == 'student'

def is_teacher(user):
    """ตรวจสอบว่าผู้ใช้เป็นอาจารย์หรือไม่"""
    return hasattr(user, 'role') and user.role == 'teacher'

def is_admin(user):
    """ตรวจสอบว่าผู้ใช้เป็นผู้ดูแลระบบหรือไม่"""
    # superuser หรือ staff สามารถเข้าถึงได้
    return user.is_superuser or user.is_staff

# ส่วนจัดการการเข้าสู่ระบบ
def login_view(request):
    """จัดการการเข้าสู่ระบบ"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            try:
                # ตรวจสอบว่าผู้ใช้มีอยู่จริง
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    if user.is_active:  # ตรวจสอบว่าได้รับการอนุมัติแล้ว
                        login(request, user)
                        messages.success(request, f"ยินดีต้อนรับ {user.username}")
                        return redirect('home')
                    else:
                        messages.warning(
                            request, 
                            "บัญชีของคุณยังไม่ได้รับการอนุมัติ กรุณารอการตรวจสอบจากเจ้าหน้าที่"
                        )
                else:
                    messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
        else:
            messages.error(request, "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
    
    return render(request, 'login.html')

@login_required
def logout_view(request):
    """จัดการการออกจากระบบ"""
    logout(request)
    return redirect('login')

def register(request):
    """จัดการการลงทะเบียนผู้ใช้ใหม่"""
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            # สร้างผู้ใช้แต่ยังไม่บันทึก
            user = form.save(commit=False)
            # ตั้งค่าข้อมูลเพิ่มเติม
            user.role = 'student'
            user.is_active = False  # ต้องแน่ใจว่าเซ็ตเป็น False
            user.set_password(form.cleaned_data['password1'])
            # บันทึกข้อมูล
            user.save()
            
            # Debug print
            print(f"DEBUG: New user registered:")
            print(f"- Username: {user.username}")
            print(f"- Active: {user.is_active}")
            print(f"- Role: {user.role}")
            
            messages.success(request, 'ลงทะเบียนสำเร็จ! กรุณารอการอนุมัติจากเจ้าหน้าที่')
            return redirect('login')
    else:
        form = StudentRegisterForm()
    return render(request, 'register.html', {'form': form})

# หน้าหลัก
def index(request):
    """แสดงหน้าหลักพร้อมกิจกรรมและประกาศ"""
    filter_type = request.GET.get('filter', 'upcoming')
    current_datetime = timezone.now()
    announcements = Announcement.objects.order_by('-created_at')
    
    # ดึงข้อมูลกิจกรรม...
    if filter_type == 'upcoming':
        activities = Activity.objects.filter(
            end_date__gte=current_datetime.date()
        ).order_by('start_date')
    elif filter_type in ['pending', 'approved', 'rejected'] and request.user.is_authenticated:
        activities = Activity.objects.filter(
            participation__student=request.user,
            participation__status=filter_type
        ).distinct()
    else:
        activities = Activity.objects.all().order_by('-start_date')

    # เพิ่มข้อมูลจำนวนผู้เข้าร่วมสำหรับแต่ละกิจกรรม
    for activity in activities:
        activity.current_participants = activity.get_current_participants()
        activity.is_activity_full = activity.is_full()
        activity.capacity_color = activity.get_capacity_color()

    context = {
        'activities': activities,
        'current_filter': filter_type,
        'announcements': announcements,
        'current_date': current_datetime.date()
    }
    return render(request, 'index.html', context)

# Activity views
def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participation = None
    status = None
    status_color = ''
    
    # ตรวจสอบสถานะการลงทะเบียน
    if request.user.is_authenticated:
        participation = Participation.objects.filter(
            activity=activity,
            student=request.user
        ).first()
        
        if participation:
            if participation.status == 'pending':
                status = "ลงทะเบียนแล้วรอการอนุมัติ"
                status_color = "bg-yellow-50"
            elif participation.status == 'approved':
                status = "อนุมัติการลงทะเบียนแล้ว"
                status_color = "bg-green-50"
            elif participation.status == 'rejected':
                status = "ไม่อนุมัติการลงทะเบียน"
                status_color = "bg-red-50"
    
    # ข้อมูลจำนวนผู้เข้าร่วม
    current_participants = activity.get_current_participants()
    
    # เงื่อนไขการแสดงปุ่มแก้ไขกิจกรรม
    can_edit = request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
    
    return render(request, 'activity_info.html', {
        'activity': activity,
        'participation': participation,
        'status': status,
        'status_color': status_color,
        'current_participants': current_participants,
        'can_edit': can_edit,
        'is_full': activity.is_full(),
        'max_participants': activity.max_participants
    })

activity_detail = activity_info  # alias สำหรับความเข้ากันได้กับ URLs เดิม

@login_required
def join_activity(request, activity_id):
    if request.method == 'POST':
        activity = get_object_or_404(Activity, id=activity_id)
        
        # ตรวจสอบว่ากิจกรรมเต็มหรือไม่
        if activity.is_full():
            return JsonResponse({
                'status': 'error',
                'message': 'ขออภัย กิจกรรมนี้มีผู้เข้าร่วมเต็มจำนวนแล้ว'
            })
            
        # ตรวจสอบว่าเคยลงทะเบียนแล้วหรือไม่
        participation, created = Participation.objects.get_or_create(
            activity=activity,
            student=request.user
        )

        if created:
            return JsonResponse({
                'status': 'success',
                'message': 'ลงทะเบียนสำเร็จ กรุณารอการอนุมัติ'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'คุณเคยลงทะเบียนกิจกรรมนี้แล้ว'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

@login_required
def activity_list(request):
    activities = Activity.objects.all()
    year = request.GET.get('year')
    month = request.GET.get('month')
    day = request.GET.get('day')
    
    if year:
        activities = activities.filter(start_date__year=year)
    if month:
        activities = activities.filter(start_date__month=month)
    if day:
        activities = activities.filter(start_date__day=day)

    current_year = datetime.now().year
    years = range(current_year - 2, current_year + 2)
    
    months = [
        (1, 'มกราคม'), (2, 'กุมภาพันธ์'), (3, 'มีนาคม'),
        (4, 'เมษายน'), (5, 'พฤษภาคม'), (6, 'มิถุนายน'),
        (7, 'กรกฎาคม'), (8, 'สิงหาคม'), (9, 'กันยายน'),
        (10, 'ตุลาคม'), (11, 'พฤศจิกายน'), (12, 'ธันวาคม')
    ]
    
    days = range(1, 32)
    
    available_months = Activity.get_unique_months()
    available_years = Activity.get_unique_years()

    context = {
        'activities': activities,
        'years': years,
        'months': months,
        'days': days,
        'selected_year': year,
        'selected_month': month,
        'selected_day': day,
        'available_months': available_months,
        'available_years': available_years
    }
    
    return render(request, 'activity_list.html', context)

# Participation views
@login_required
def track_participation(request):
    participations = Participation.objects.filter(student=request.user).select_related('activity')
    participation = participations.first()

    context = {
        'participations': participations,
        'participation': participation,
    }
    return render(request, 'track_participation.html', context)

@login_required
@user_passes_test(is_admin)
def update_participation_status(request, participation_id):
    if request.method == 'POST':
        participation = get_object_or_404(Participation, id=participation_id)
        try:
            data = json.loads(request.body.decode('utf-8'))
            new_status = data.get('status')
            if new_status in ['approved', 'rejected']:
                participation.status = new_status
                participation.save()
                return JsonResponse({
                    'status': 'success',
                    'new_status': new_status
                })
            return JsonResponse({
                'status': 'error',
                'message': 'สถานะไม่ถูกต้อง'
            }, status=400)
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({
                'status': 'error',
                'message': 'ข้อมูลที่ส่งมาไม่ถูกต้อง'
            }, status=400)
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@login_required
@csrf_protect
def upload_proof(request):
    """แสดงหน้าอัพโหลดหลักฐานกิจกรรม"""
    activity_filter = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')

    # ดึงกิจกรรมที่ผู้ใช้ได้รับการอนุมัติแล้ว
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    # แปลง participations ให้อยู่ในรูปแบบที่ template ต้องการ
    registrations = []
    for p in participations:
        # อ้างอิง ActivityRegistration ถ้ามี หรือสร้าง dictionary เปล่า
        try:
            reg = ActivityRegistration.objects.get(user=request.user, activity=p.activity)
            has_proof = bool(reg.proof_image)
            registrations.append({
                'activity': p.activity,
                'registration_date': p.joined_at,
                'has_proof': has_proof,
                'proof_image': reg.proof_image if has_proof else None,
                'proof_upload_date': reg.proof_upload_date if has_proof else None,
                'is_approved': reg.is_approved if has_proof else False,
            })
        except ActivityRegistration.DoesNotExist:
            # กิจกรรมที่ยังไม่มีการอัพโหลดหลักฐาน
            registrations.append({
                'activity': p.activity,
                'registration_date': p.joined_at,
                'has_proof': False,
                'proof_image': None,
                'proof_upload_date': None,
                'is_approved': False,
            })

    # จัดการการอัพโหลดหลักฐาน
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
            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),
                    'is_approved': False  # กำหนดค่าเป็น False เสมอ
                }
            )

            return JsonResponse({
                'success': True,
                'image_url': registration.proof_image.url,
                'upload_date': registration.proof_upload_date.strftime("%d/%m/%Y %H:%M"),
                'is_approved': False  # ส่งค่า is_approved ไปด้วย
            })

        except Exception as e:
            print(f"DEBUG: Error uploading proof - {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'เกิดข้อผิดพลาด: {str(e)}'
            })

    # ใช้ filters ที่มีอยู่เดิม
    if activity_filter:
        filtered_registrations = []
        for reg in registrations:
            if str(reg['activity'].id) == activity_filter:
                filtered_registrations.append(reg)
        registrations = filtered_registrations
        
    if date_filter:
        filtered_registrations = []
        for reg in registrations:
            if reg['proof_upload_date'] and reg['proof_upload_date'].strftime('%Y-%m-%d') == date_filter:
                filtered_registrations.append(reg)
        registrations = filtered_registrations
        
    if month_filter:
        filtered_registrations = []
        for reg in registrations:
            if reg['proof_upload_date'] and reg['proof_upload_date'].month == int(month_filter):
                filtered_registrations.append(reg)
        registrations = filtered_registrations
        
    if year_filter:
        filtered_registrations = []
        for reg in registrations:
            if reg['proof_upload_date'] and reg['proof_upload_date'].year == int(year_filter):
                filtered_registrations.append(reg)
        registrations = filtered_registrations

    # เพิ่มข้อมูลเดือนและปีสำหรับ filter
    current_year = timezone.now().year
    years = range(current_year - 2, current_year + 1)
    months = [
        {'number': i, 'name': month} for i, month in enumerate([
            'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน',
            'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
            'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
        ], 1)
    ]

    # ส่งข้อมูลไปยัง template
    context = {
        'registrations': registrations,
        'activities': Activity.objects.all(),
        'years': years,
        'months': months,
        'selected_activity': activity_filter,
        'selected_date': date_filter,
        'selected_month': month_filter,
        'selected_year': year_filter
    }

    return render(request, 'upload_proof.html', context)

# Profile views
@login_required
def edit_profile(request):
    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("home")
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, "edit_profile.html", {"form": form})

@login_required
def edit_userprofile(request):
    """หน้าแก้ไขข้อมูลส่วนตัวของผู้ใช้"""
    user = request.user
    
    # รับค่า filter จาก URL parameters
    month = request.GET.get('month')  # เพิ่มบรรทัดนี้
    year = request.GET.get('year')    # เพิ่มบรรทัดนี้
    
    if request.method == 'POST':
        # รับข้อมูลจากฟอร์ม
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        student_id = request.POST.get('student_id', '')
        
        # อัพเดทข้อมูลผู้ใช้
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.student_id = student_id
        user.save()
        
        messages.success(request, 'อัพเดทข้อมูลส่วนตัวเรียบร้อยแล้ว')
        return redirect('edit_userprofile')
    
    # สร้าง form สำหรับแสดงข้อมูลผู้ใช้
    form = UserProfileForm(instance=user)
    
    participations = Participation.objects.filter(
        student=user
    ).select_related('activity')
    
    activities_with_proof = []
    for participation in participations:
        try:
            reg = ActivityRegistration.objects.get(
                user=request.user,
                activity=participation.activity
            )
            has_proof = bool(reg.proof_image)
            proof_approved = reg.is_approved if has_proof else False
        except ActivityRegistration.DoesNotExist:
            has_proof = False
            proof_approved = False
        
        activities_with_proof.append({
            'activity': participation.activity,
            'status': participation.status,
            'joined_at': participation.joined_at,
            'has_proof': has_proof,
            'proof_approved': proof_approved
        })
    
    available_months = []
    available_years = []
    
    if participations.exists():
        years = participations.dates('activity__start_date', 'year')
        available_years = [year.year for year in years]
        
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

    context = {
        'form': form,
        'user': user,
        'activities': activities_with_proof,
        'available_months': available_months,
        'available_years': available_years,
        'selected_month': month,
        'selected_year': year
    }
    
    return render(request, 'edit_userprofile.html', context)

# จัดการผู้เข้าร่วมกิจกรรม
@login_required
def get_participants(request, activity_id):
    """ดึงข้อมูลผู้เข้าร่วมกิจกรรม"""
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

@login_required
@user_passes_test(is_admin)
def manage_participation(request):
    """จัดการการเข้าร่วมกิจกรรมทั้งหมด"""
    participations = Participation.objects.all().select_related('student', 'activity')
    
    # Filter options
    status = request.GET.get('status')
    activity = request.GET.get('activity')
    
    if status:
        participations = participations.filter(status=status)
    if activity:
        participations = participations.filter(activity_id=activity)
        
    context = {
        'participations': participations,
        'activities': Activity.objects.all()
    }
    return render(request, 'manage_participation.html', context)

@login_required
@user_passes_test(is_admin)
def add_activity(request):
    """เพิ่มกิจกรรมใหม่"""
    # ใช้ print เพื่อดีบัก
    print("เริ่มต้นฟังก์ชัน add_activity")
    
    # เพิ่ม ImageFormSet ถ้าคุณใช้
    ImageFormSet = inlineformset_factory(
        Activity,
        ActivityImage,
        fields=('image',),
        extra=1,
        can_delete=False
    )
    
    if request.method == 'POST':
        activity_form = ActivityForm(request.POST)
        formset = ImageFormSet(request.POST, request.FILES)
        
        if activity_form.is_valid() and formset.is_valid():
            # บันทึกกิจกรรม
            activity = activity_form.save()
            
            # บันทึกรูปภาพ (ถ้ามี)
            formset.instance = activity
            formset.save()
            
            messages.success(request, 'เพิ่มกิจกรรมใหม่เรียบร้อยแล้ว')
            return redirect('activity_list')
        else:
            print("ฟอร์มไม่ถูกต้อง:", activity_form.errors, formset.errors)
    else:
        activity_form = ActivityForm()
        formset = ImageFormSet()
    
    # แสดงตัวแปร debug เพื่อตรวจสอบ
    print(f"activity_form fields: {activity_form.fields}")
    print(f"formset: {formset}")
    
    # ส่งฟอร์มไปยังเทมเพลต
    context = {
        'activity_form': activity_form,  # ชื่อต้องตรงกับที่ใช้ในเทมเพลต
        'formset': formset
    }
    
    return render(request, 'add_activity.html', context)

@login_required
@user_passes_test(is_admin)
def participation_report(request):
    """สร้างรายงานการเข้าร่วมกิจกรรม"""
    # ดึงข้อมูลการเข้าร่วมทั้งหมด
    participations = Participation.objects.all().select_related(
        'student', 'activity'
    ).order_by('-activity__start_date')

    # Filter options
    activity_id = request.GET.get('activity')
    status = request.GET.get('status')
    year = request.GET.get('year')
    month = request.GET.get('month')

    # Apply filters
    if activity_id:
        participations = participations.filter(activity_id=activity_id)
    if status:
        participations = participations.filter(status=status)
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)

    # Get unique values for filter dropdowns
    activities = Activity.objects.all()
    years = participations.dates('activity__start_date', 'year')
    months = [
        {'number': i, 'name': month} for i, month in enumerate([
            'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน',
            'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
            'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
        ], 1)
    ]
    
    status_choices = [
        ('pending', 'รอการอนุมัติ'),
        ('approved', 'อนุมัติแล้ว'),
        ('rejected', 'ไม่อนุมัติ')
    ]

    context = {
        'participations': participations,
        'activities': activities,
        'years': years,
        'months': months,
        'status_choices': status_choices,
        'selected_activity': activity_id,
        'selected_status': status,
        'selected_year': year,
        'selected_month': month
    }

    return render(request, 'participation_report.html', context)

@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    """จัดการแก้ไขข้อมูลผู้ใช้"""
    user = get_object_or_404(MyUser, pk=user_id)
    
    if request.method == 'POST':
        form = MyUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขข้อมูลผู้ใช้สำเร็จ')
            return redirect('user_list')  # หรือ URL ที่ต้องการให้ redirect ไป
    else:
        form = MyUserForm(instance=user)
    
    return render(request, 'edit_user.html', {
        'form': form,
        'user': user
    })

@login_required
def my_activities(request):
    """แสดงกิจกรรมที่ผู้ใช้เข้าร่วม"""
    # Filter options
    year = request.GET.get('year')
    month = request.GET.get('month')
    status = request.GET.get('status')

    # ดึงข้อมูลการเข้าร่วมทั้งหมดของผู้ใช้
    participations = Participation.objects.filter(
        student=request.user
    ).select_related('activity')

    # Apply filters
    if year:
        participations = participations.filter(activity__start_date__year=year)
    if month:
        participations = participations.filter(activity__start_date__month=month)
    if status:
        participations = participations.filter(status=status)

    # Get filter options
    years = participations.dates('activity__start_date', 'year')
    months = [
        {'number': i, 'name': month} for i, month in enumerate([
            'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน',
            'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
            'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
        ], 1)
    ]
    
    status_choices = [
        ('pending', 'รอการอนุมัติ'),
        ('approved', 'อนุมัติแล้ว'),
        ('rejected', 'ไม่อนุมัติ')
    ]

    context = {
        'participations': participations,
        'years': years,
        'months': months,
        'status_choices': status_choices,
        'selected_year': year,
        'selected_month': month,
        'selected_status': status
    }

    return render(request, 'my_activities.html', context)

@login_required
@staff_member_required  # เพิ่มตรงนี้เพื่อจำกัดให้เฉพาะ staff และ admin เท่านั้น
def user_upload_proof_list(request):
    """แสดงรายการหลักฐานที่ผู้ใช้อัพโหลดแล้วสำหรับ staff/admin"""
    # สำหรับ staff/admin ให้แสดงหลักฐานของทุกคน
    activity_id = request.GET.get('activity')
    date_filter = request.GET.get('upload_date')
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    # ดึงข้อมูลการลงทะเบียนที่มีการอัพโหลดรูปภาพ (ของทุกคน)
    registrations = ActivityRegistration.objects.filter(
        proof_image__isnull=False  # เฉพาะที่มีการอัพโหลดรูปแล้ว
    ).select_related('user', 'activity')  # เพิ่ม 'user' ด้วย
    
    # Debug prints
    print(f"DEBUG: Found {registrations.count()} registrations with proofs")

    # ใช้ filters
    if activity_id:
        registrations = registrations.filter(activity_id=activity_id)
    if date_filter:
        registrations = registrations.filter(proof_upload_date__date=date_filter)
    if month:
        registrations = registrations.filter(proof_upload_date__month=month)
    if year:
        registrations = registrations.filter(proof_upload_date__year=year)

    # สร้าง registrations_data ใหม่พร้อมข้อมูลนักศึกษา
    registrations_data = []
    for reg in registrations:
        # มั่นใจว่า status ถูกกำหนดจาก is_approved
        status = 'approved' if reg.is_approved else 'pending'
        
        try:
            # ตรวจสอบว่า proof_image ไฟล์ยังมีอยู่จริง
            if reg.proof_image and reg.proof_image.storage.exists(reg.proof_image.name):
                proof_image_url = reg.proof_image.url
            else:
                proof_image_url = None
        except Exception as e:
            print(f"Error accessing proof image for registration {reg.id}: {str(e)}")
            proof_image_url = None
            
        registrations_data.append({
            'id': reg.id,
            'activity': reg.activity,
            'user': reg.user,  # เพิ่มข้อมูลผู้ใช้
            'student_id': reg.user.student_id if hasattr(reg.user, 'student_id') else '-',
            'branch': reg.user.get_branch_display() if hasattr(reg.user, 'get_branch_display') else '-',
            'year': reg.user.year if hasattr(reg.user, 'year') else '-',
            'proof_image': proof_image_url,  # ใช้ URL ที่ตรวจสอบแล้ว
            'proof_upload_date': reg.proof_upload_date,
            'is_approved': reg.is_approved,
            'status': status,
            'has_proof': True if proof_image_url else False  # ตรวจสอบว่ามีหลักฐานจริงหรือไม่
        })

    # ดึงกิจกรรมทั้งหมดสำหรับ filter
    activities = Activity.objects.all()

    # เตรียมข้อมูลวันที่สำหรับ filter
    available_dates = registrations.exclude(
        proof_upload_date__isnull=True
    ).dates('proof_upload_date', 'day')

    # เตรียมข้อมูล years และ months สำหรับ filter
    years = registrations.exclude(
        proof_upload_date__isnull=True
    ).dates('proof_upload_date', 'year')
    
    context = {
        'registrations': registrations_data,
        'activities': activities,
        'available_dates': available_dates,
        'selected_activity': activity_id,
        'selected_date': date_filter,
        'selected_month': month,
        'selected_year': year,
        'years': [y.year for y in years],  # แปลงเป็นปีปกติ
        'months': [
            {'number': i, 'name': month} for i, month in enumerate([
                'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 
                'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
                'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
            ], 1)
        ]
    }
    
    return render(request, 'user_upload_proof_list.html', context)

@login_required
def delete_my_proof(request, reg_id):
    """ลบหลักฐานการเข้าร่วมกิจกรรม (สำหรับนักศึกษาลบของตัวเอง)"""
    if request.method == 'POST':
        try:
            # ใช้ activity_id แทน reg_id
            activity = get_object_or_404(Activity, id=reg_id)
            
            # ค้นหา registration ด้วย user และ activity
            registration = ActivityRegistration.objects.get(
                user=request.user,
                activity=activity
            )
            
            # ลบรูปภาพ
            if registration.proof_image:
                # บันทึกพาธก่อนลบเพื่อ debug
                old_path = registration.proof_image.path if hasattr(registration.proof_image, 'path') else None
                print(f"Deleting image: {old_path}")
                
                # ลบไฟล์รูปภาพ
                registration.proof_image.delete(save=False)
                registration.proof_upload_date = None
                registration.save()
                
                print(f"Image deleted successfully")
            
            return JsonResponse({'status': 'success'})
            
        except ActivityRegistration.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'ไม่พบข้อมูลการลงทะเบียน'
            }, status=404)
        except Exception as e:
            print(f"Error deleting proof: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

# ส่วนฟังก์ชัน delete_proof อันที่สอง (สำหรับ staff/admin) ให้คงไว้ตามเดิม
@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def delete_proof(request, proof_id):
    """ลบหลักฐาน (สำหรับ staff/admin)"""
    if request.method == 'POST':
        try:
            proof = ActivityRegistration.objects.get(id=proof_id)
            
            # ลบไฟล์รูปภาพ
            if proof.proof_image:
                if proof.proof_image.storage.exists(proof.proof_image.name):
                    proof.proof_image.delete()  # ลบไฟล์จาก storage
            
            # ลบ record
            proof.proof_image = None
            proof.proof_upload_date = None
            proof.is_approved = False
            proof.save()
            
            return JsonResponse({'success': True})
        except ActivityRegistration.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'ไม่พบหลักฐาน'})
        except Exception as e:
            print(f"Error deleting proof: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

@login_required
@user_passes_test(is_admin)
def show_all_proofs(request):
    """แสดงหลักฐานทั้งหมดสำหรับผู้ดูแลระบบพร้อมตัวกรอง"""
    # เตรียมตัวแปรสำหรับ filter
    activity_id = request.GET.get('activity')
    student_id = request.GET.get('student_id')
    year = request.GET.get('year')
    status = request.GET.get('status')
    
    # ดึงข้อมูลหลักฐานทั้งหมด
    proofs = ActivityRegistration.objects.filter(
        proof_image__isnull=False
    ).select_related('user', 'activity')
    
    # ใช้ filters
    if activity_id:
        proofs = proofs.filter(activity_id=activity_id)
    if student_id:
        proofs = proofs.filter(user__student_id__contains=student_id)
    if year:
        proofs = proofs.filter(user__year=year)  # ตรวจสอบว่า MyUser มี field 'year'
    if status:
        if status == 'approved':
            proofs = proofs.filter(is_approved=True)
        elif status == 'pending':
            proofs = proofs.filter(is_approved=False)
    
    # ดึงข้อมูลสำหรับ dropdowns
    activities = Activity.objects.all()
    # ไม่ใช้ branch เพราะ CustomUser อาจไม่มีฟิลด์นี้
    # branches = MyUser.objects.values_list('branch', flat=True).distinct()
    years = MyUser.objects.values_list('year', flat=True).distinct()
    
    context = {
        'proofs': proofs,
        'activities': activities,
        # 'branches': branches,  # ไม่ใช้ branch
        'years': years,
        'selected_activity': activity_id,
        'selected_student_id': student_id,
        # 'selected_branch': branch,  # ไม่ใช้ branch
        'selected_year': year,
        'selected_status': status
    }
    
    return render(request, 'show_all_proofs.html', context)

@login_required
@user_passes_test(is_admin)
def manage_proof(request, activity_id, action):
    """จัดการหลักฐานการเข้าร่วมกิจกรรม"""
    if request.method == 'POST':
        proof = get_object_or_404(ActivityRegistration, id=activity_id)
        if action == 'approve':
            proof.status = 'approved'
        elif action == 'reject':
            proof.status = 'rejected'
        proof.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@user_passes_test(is_admin)
def manage_participations(request):
    """จัดการการเข้าร่วมกิจกรรมทั้งหมด"""
    # Query participations พร้อมข้อมูลที่เกี่ยวข้อง
    participations = Participation.objects.select_related(
        'student', 
        'activity'
    ).order_by('-joined_at')
    
    # Filter options
    status = request.GET.get('status')
    activity_id = request.GET.get('activity')
    
    if status:
        participations = participations.filter(status=status)
    if activity_id:
        participations = participations.filter(activity_id=activity_id)
    
    # Debug prints
    print(f"DEBUG: Found {participations.count()} participations")
    for p in participations:
        print(f"DEBUG: {p.student.username} - {p.activity.name} - {p.status}")
    
    context = {
        'participations': participations,
        'activities': Activity.objects.all(),
        'status_choices': [
            ('pending', 'รอการอนุมัติ'),
            ('approved', 'อนุมัติแล้ว'),
            ('rejected', 'ไม่อนุมัติ')
        ],
        'selected_status': status,
        'selected_activity': activity_id
    }
    
    return render(request, 'manage_participation.html', context)

@login_required
@user_passes_test(is_admin)
def student_list(request):
    """แสดงรายชื่อนักศึกษาทั้งหมด"""
    students = MyUser.objects.filter(role='student')
    
    print(f"DEBUG: Found {students.count()} students")
    
    # ถ้ามีการกรองเพิ่มเติมใน student_list.html ให้ใส่โค้ดตรงนี้
    selected_branches = request.GET.getlist('branch')
    selected_years = request.GET.getlist('year')
    
    if selected_branches:
        print(f"DEBUG: Filtering by branches: {selected_branches}")
        students = students.filter(branch__in=selected_branches)
    if selected_years:
        print(f"DEBUG: Filtering by years: {selected_years}")
        students = students.filter(year__in=selected_years)
    
    print(f"DEBUG: After filtering, found {students.count()} students")
    
    # สร้าง BRANCH_CHOICES แบบคงที่
    BRANCH_CHOICES = [
        ('it', 'เทคโนโลยีสารสนเทศ'),
        ('cs', 'วิทยาการคอมพิวเตอร์'),
        ('dse', 'วิทยาการข้อมูลและนวัตกรรมซอฟต์แวร์'),
        # เพิ่มสาขาอื่นๆ ตามที่มีในระบบของคุณ
    ]
    
    # เตรียมข้อมูลสำหรับส่งไปยัง template
    context = {
        'students': students,
        'selected_branches': selected_branches,
        'selected_years': selected_years,
        'BRANCH_CHOICES': BRANCH_CHOICES
    }
    
    return render(request, 'student_list.html', context)

@login_required
@user_passes_test(is_admin)
def generate_report(request):
    """หน้าจอสำหรับเลือกเงื่อนไขในการออกรายงาน"""
    
    # ดึงข้อมูลกิจกรรมทั้งหมดที่มีในระบบ
    activities = Activity.objects.all().order_by('-start_date')
    
    # Debug print จำนวนกิจกรรมที่พบ
    print(f"DEBUG: Found {activities.count()} activities for report")
    
    # ส่งข้อมูลไปยังเทมเพลต
    context = {
        'activities': activities
    }
    
    return render(request, 'generate_report.html', context)

@login_required
@user_passes_test(is_admin)
def download_report(request):
    """ดาวน์โหลดรายงาน PDF"""
    activity_id = request.GET.get('activity', 'all')
    
    # ตรวจสอบว่าเลือกกิจกรรมเฉพาะหรือทั้งหมด
    if activity_id == 'all':
        participations = Participation.objects.all().select_related('student', 'activity')
        filename = "all_activities_report.pdf"
    else:
        activity = get_object_or_404(Activity, id=activity_id)
        participations = Participation.objects.filter(activity=activity).select_related('student')
        filename = f"activity_{activity_id}_report.pdf"
    
    # เพิ่มข้อมูลหลักฐาน
    participation_data = []
    for p in participations:
        # ตรวจสอบหลักฐานการเข้าร่วม
        try:
            reg = ActivityRegistration.objects.get(
                user=p.student,
                activity=p.activity
            )
            has_proof = bool(reg.proof_image)
            proof_status = "อนุมัติแล้ว" if reg.is_approved else "รอการอนุมัติ" if has_proof else "ยังไม่มีหลักฐาน"
        except ActivityRegistration.DoesNotExist:
            has_proof = False
            proof_status = "ยังไม่มีหลักฐาน"
        
        # แปลงสถานะการลงทะเบียน
        if p.status == 'approved':
            register_status = "อนุมัติแล้ว"
        elif p.status == 'pending':
            register_status = "รอการอนุมัติ"
        else:
            register_status = "ไม่อนุมัติ"
            
        participation_data.append({
            'student': p.student,
            'activity': p.activity,
            'register_status': register_status,
            'proof_status': proof_status
        })
    
    # สร้าง PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        import os
        
        # ลงทะเบียนฟอนต์ไทย
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts', 'THSarabunNew.ttf')
        pdfmetrics.registerFont(TTFont('THSarabun', font_path))
        
        # สร้าง Document - ปรับระยะขอบให้น้อยลงเพื่อให้มีพื้นที่ตารางมากขึ้น
        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=36,  # 0.5 นิ้ว
            leftMargin=36,   # 0.5 นิ้ว
            topMargin=72,    # 1 นิ้ว
            bottomMargin=36  # 0.5 นิ้ว
        )
        
        # คำนวณความกว้างที่ใช้ได้
        available_width = doc.width
        
        # สร้าง style
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='ThaiHeading',
            fontName='THSarabun',
            fontSize=22,
            alignment=1,  # center
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name='ThaiNormal',
            fontName='THSarabun',
            fontSize=16,
            alignment=1,  # center
            spaceAfter=6
        ))
        
        # สร้าง story (content)
        story = []
        
        # เพิ่มโลโก้
        logo_path = 'E:/Pai E/เรียนมหาลัย/project จบ/Project_STCAM/static/image/cropped-sdu-logo-th-h1024.png'
        if os.path.exists(logo_path):
            im = Image(logo_path)
            im.drawHeight = 1.2 * inch
            im.drawWidth = 1.2 * inch
            im.hAlign = 'CENTER'
            story.append(im)
            story.append(Spacer(1, 12))
        
        # เพิ่มหัวข้อ
        story.append(Paragraph("รายงานการเข้าร่วมกิจกรรมนักศึกษา", styles["ThaiHeading"]))
        story.append(Paragraph(f"วันที่ออกรายงาน: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles["ThaiNormal"]))
        
        if activity_id != 'all':
            story.append(Paragraph(f"กิจกรรม: {activity.name}", styles["ThaiNormal"]))
            story.append(Paragraph(f"วันที่จัดกิจกรรม: {activity.start_date.strftime('%d/%m/%Y')}", styles["ThaiNormal"]))
        else:
            story.append(Paragraph("กิจกรรมทั้งหมด", styles["ThaiNormal"]))
        
        story.append(Spacer(1, 12))
        
        # สร้างตาราง - ปรับขนาดคอลัมน์ให้พอดีกับหน้ากระดาษ
        if activity_id == 'all':
            # คอลัมน์สำหรับรายงานกิจกรรมทั้งหมด - ปรับขนาดให้พอดีหน้า
            data = [['ลำดับ', 'ชื่อ-นามสกุล', 'รหัสนักศึกษา', 'คณะ/สาขา', 'ชั้นปี', 'กิจกรรม', 'วันที่กิจกรรม', 'สถานะลงทะเบียน', 'สถานะหลักฐาน']]
            
            # จัดสรรความกว้างคอลัมน์ตามสัดส่วน
            col_widths = [
                available_width * 0.05,  # ลำดับ
                available_width * 0.15,  # ชื่อ-นามสกุล
                available_width * 0.10,  # รหัสนักศึกษา
                available_width * 0.10,  # คณะ/สาขา
                available_width * 0.05,  # ชั้นปี
                available_width * 0.15,  # กิจกรรม
                available_width * 0.10,  # วันที่กิจกรรม
                available_width * 0.15,  # สถานะลงทะเบียน
                available_width * 0.15   # สถานะหลักฐาน
            ]
            
            for i, p in enumerate(participation_data, 1):
                student = p['student']
                data.append([
                    i,
                    student.get_full_name(),
                    student.student_id or "-",
                    getattr(student, 'branch', '-'),
                    getattr(student, 'year', '-'),
                    p['activity'].name,
                    p['activity'].start_date.strftime('%d/%m/%Y'),
                    p['register_status'],
                    p['proof_status']
                ])
                
        else:
            # คอลัมน์สำหรับรายงานกิจกรรมเดียว - ปรับขนาดให้พอดีหน้า
            data = [['ลำดับ', 'ชื่อ-นามสกุล', 'รหัสนักศึกษา', 'คณะ/สาขา', 'ชั้นปี', 'วันที่กิจกรรม', 'สถานะลงทะเบียน', 'สถานะหลักฐาน']]
            
            # จัดสรรความกว้างคอลัมน์ตามสัดส่วน
            col_widths = [
                available_width * 0.05,  # ลำดับ
                available_width * 0.18,  # ชื่อ-นามสกุล
                available_width * 0.12,  # รหัสนักศึกษา
                available_width * 0.12,  # คณะ/สาขา
                available_width * 0.08,  # ชั้นปี
                available_width * 0.15,  # วันที่กิจกรรม
                available_width * 0.15,  # สถานะลงทะเบียน
                available_width * 0.15   # สถานะหลักฐาน
            ]
            
            for i, p in enumerate(participation_data, 1):
                student = p['student']
                data.append([
                    i,
                    student.get_full_name(),
                    student.student_id or "-",
                    getattr(student, 'branch', '-'),
                    getattr(student, 'year', '-'),
                    p['activity'].start_date.strftime('%d/%m/%Y'),
                    p['register_status'],
                    p['proof_status']
                ])
        
        # สร้าง Table พร้อมกำหนดความกว้างคอลัมน์
        table = Table(data, repeatRows=1, colWidths=col_widths)
        
        # ฟังก์ชันกำหนดสีตามสถานะ
        def get_status_color(status):
            if 'อนุมัติแล้ว' in status:
                return colors.lightgreen
            elif 'รอการอนุมัติ' in status:
                return colors.lightyellow
            else:
                return colors.lightcoral

        # กำหนด style พื้นฐาน - ปรับขนาดฟอนต์ให้เล็กลงเพื่อให้พอดีกับตาราง
        table_style = [
            ('FONT', (0, 0), (-1, 0), 'THSarabun', 14),  # หัวตาราง
            ('FONT', (0, 1), (-1, -1), 'THSarabun', 13), # เนื้อหา
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
            # แก้ไขความสูงของแถว
            ('ROWHEIGHT', (0, 0), (-1, -1), 0.4*cm),
        ]
        
        # กำหนดสีพื้นหลังสถานะสำหรับแต่ละแถว
        for i, row in enumerate(data[1:], 1):
            # กำหนดสีพื้นหลังสำหรับสถานะลงทะเบียนและสถานะหลักฐาน
            if activity_id == 'all':
                reg_status_col = 7  # คอลัมน์สถานะลงทะเบียน
                proof_status_col = 8  # คอลัมน์สถานะหลักฐาน
            else:
                reg_status_col = 6  # คอลัมน์สถานะลงทะเบียน
                proof_status_col = 7  # คอลัมน์สถานะหลักฐาน
            
            table_style.append(('BACKGROUND', (reg_status_col, i), (reg_status_col, i), get_status_color(row[reg_status_col])))
            table_style.append(('BACKGROUND', (proof_status_col, i), (proof_status_col, i), get_status_color(row[proof_status_col])))
        
        table.setStyle(TableStyle(table_style))
        
        # จัดการการขึ้นหน้าใหม่อัตโนมัติ โดยการตั้งค่า splitByRow=True
        table._splittingEnabled = 1  # เปิดใช้งานการแบ่งตาราง
        table._splitByRow = 1        # แบ่งตารางตามแถว
        
        story.append(table)
        
        # สร้าง PDF
        doc.build(story)
        
        return response
        
    except ImportError as e:
        print(f"ImportError: {str(e)}")
        return HttpResponse("ไม่สามารถสร้าง PDF ได้ กรุณาติดตั้ง ReportLab ก่อน: pip install reportlab")
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return HttpResponse(f"เกิดข้อผิดพลาดในการสร้าง PDF: {str(e)}")

@login_required
@user_passes_test(is_admin)
def pending_users(request):
    """แสดงรายการผู้ใช้ที่รอการอนุมัติ"""
    # แก้จาก user_type เป็น role
    pending = CustomUser.objects.filter(
        is_active=False,
        role='student'  # เปลี่ยนจาก user_type เป็น role
    ).order_by('-date_joined')
    
    # Debug prints
    print(f"DEBUG: Found {pending.count()} pending users")
    for user in pending:
        print(f"DEBUG: User found - {user.username} (active={user.is_active}, type={user.user_type})")

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if user_id and action:
            try:
                user = CustomUser.objects.get(id=user_id)  # เปลี่ยนจาก MyUser เป็น CustomUser
                if action == 'approve':
                    user.is_active = True
                    user.save()
                    messages.success(request, f'อนุมัติผู้ใช้ {user.username} เรียบร้อยแล้ว')
                elif action == 'reject':
                    user.delete()
                    messages.success(request, f'ปฏิเสธผู้ใช้ {user.username} เรียบร้อยแล้ว')
            except CustomUser.DoesNotExist:
                messages.error(request, 'ไม่พบข้อมูลผู้ใช้')

    context = {
        'pending_users': pending,
        'is_superuser': request.user.is_superuser,
        'is_staff': request.user.is_staff
    }
    
    return render(request, 'pending_users.html', context)

def staff_register(request):
    """ลงทะเบียนสำหรับเจ้าหน้าที่"""
    if request.method == 'POST':
        form = AdminRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.role = 'admin'  # เปลี่ยนจาก user_type เป็น role
            user.is_active = True
            user.save()
            messages.success(request, 'ลงทะเบียนสำเร็จ กรุณาเข้าสู่ระบบ')
            return redirect('login')
    else:
        form = AdminRegisterForm()
    return render(request, 'staff_register.html', {'form': form})

def session_expired(request):
    """หน้าแจ้งเตือนเมื่อ session หมดอายุ"""
    return render(request, 'session_expired.html')

@login_required
@user_passes_test(is_admin)
def reject_user(request, user_id):
    """ปฏิเสธผู้ใช้งาน"""
    if request.method == 'POST':
        user = get_object_or_404(MyUser, id=user_id, is_active=False)
        username = user.username
        user.delete()
        messages.success(request, f'ปฏิเสธผู้ใช้ {username} เรียบร้อยแล้ว')
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=405)

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def update_proof_status(request, proof_id):
    """อัพเดทสถานะการอนุมัติหลักฐาน"""
    if request.method == 'POST':
        try:
            status = request.POST.get('status')
            # Debug print
            print(f"DEBUG: Updating proof {proof_id} to status: {status}")
            
            if status not in ['approved', 'rejected']:
                return JsonResponse({
                    'success': False, 
                    'message': 'สถานะไม่ถูกต้อง'
                })
                
            # หา ActivityRegistration ด้วย ID
            registration = ActivityRegistration.objects.get(id=proof_id)
            
            # อัพเดทสถานะการอนุมัติ
            if status == 'approved':
                registration.is_approved = True
            else:  # rejected
                registration.is_approved = False
            
            registration.save()
            
            # Debug
            print(f"DEBUG: Updated proof {proof_id} to status: {status}, is_approved: {registration.is_approved}")
            
            return JsonResponse({
                'success': True,
                'message': f'อัพเดทสถานะเป็น "{status}" สำเร็จ',
                'is_approved': registration.is_approved
            })
            
        except ActivityRegistration.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'ไม่พบข้อมูลหลักฐาน'
            }, status=404)
        except Exception as e:
            print(f"ERROR updating proof status: {str(e)}")
            return JsonResponse({
                'success': False, 
                'message': f'เกิดข้อผิดพลาด: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False, 
        'message': 'Method not allowed'
    }, status=405)

@login_required
@user_passes_test(is_admin)
def edit_activity(request, activity_id):
    """แก้ไขข้อมูลกิจกรรม"""
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ใช้ ImageFormSet เหมือนที่ใช้ในการสร้าง
    ImageFormSet = inlineformset_factory(
        Activity,
        ActivityImage,
        fields=('image',),
        extra=1,
        can_delete=True
    )
    
    if request.method == 'POST':
        activity_form = ActivityForm(request.POST, instance=activity)
        formset = ImageFormSet(request.POST, request.FILES, instance=activity)
        
        if activity_form.is_valid() and formset.is_valid():
            # บันทึกกิจกรรม
            activity = activity_form.save()
            
            # บันทึกรูปภาพ
            formset.save()
            
            messages.success(request, 'แก้ไขกิจกรรมเรียบร้อยแล้ว')
            return redirect('activity_info', activity_id=activity.id)
        else:
            print("ฟอร์มไม่ถูกต้อง:", activity_form.errors, formset.errors)
    else:
        activity_form = ActivityForm(instance=activity)
        formset = ImageFormSet(instance=activity)
    
    # ส่งฟอร์มไปยังเทมเพลต
    context = {
        'activity_form': activity_form,
        'formset': formset,
        'activity': activity,
        'is_edit': True
    }
    
    return render(request, 'add_activity.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def delete_proof(request, proof_id):
    """ลบหลักฐาน (สำหรับ staff/admin)"""
    if request.method == 'POST':
        try:
            proof = ActivityRegistration.objects.get(id=proof_id)
            
            # ลบไฟล์รูปภาพ
            if proof.proof_image:
                if proof.proof_image.storage.exists(proof.proof_image.name):
                    proof.proof_image.delete()  # ลบไฟล์จาก storage
            
            # ลบ record
            proof.proof_image = None
            proof.proof_upload_date = None
            proof.is_approved = False
            proof.save()
            
            return JsonResponse({'success': True})
        except ActivityRegistration.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'ไม่พบหลักฐาน'})
        except Exception as e:
            print(f"Error deleting proof: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def update_multiple_proofs(request):
    """อัพเดทสถานะหลายรายการ"""
    if request.method == 'POST':
        try:
            proof_ids = json.loads(request.POST.get('proof_ids', '[]'))
            status = request.POST.get('status')
            
            if not proof_ids or status not in ['approved', 'rejected']:
                return JsonResponse({
                    'success': False, 
                    'message': 'ข้อมูลไม่ถูกต้อง'
                })
            
            # อัพเดทสถานะทุกรายการ
            is_approved = (status == 'approved')
            
            updated_count = ActivityRegistration.objects.filter(
                id__in=proof_ids
            ).update(is_approved=is_approved)
            
            return JsonResponse({
                'success': True,
                'count': updated_count
            })
        except Exception as e:
            print(f"Error updating multiple proofs: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)