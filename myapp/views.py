from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import StudentRegisterForm, AdminRegisterForm
from .models import Activity, Participation

# ฟังก์ชันตรวจสอบว่าเป็น admin หรือไม่
def is_admin(user):
    return user.user_type == 'admin'

# ฟังก์ชันสำหรับหน้าแรก
def index(request):
    return render(request, 'index.html')  # หน้าแรก

# ฟังก์ชันสำหรับการลงทะเบียนผู้ใช้
def register(request):
    if request.method == 'POST':
        user_type = request.POST.get('user_type')  # รับ user type (student หรือ admin)
        if user_type == 'student':
            form = StudentRegisterForm(request.POST)
        else:
            form = AdminRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = user_type  # กำหนด user type
            user.save()
            login(request, user)  # ล็อกอินอัตโนมัติหลังสมัคร
            return redirect('index')  # กลับไปหน้าแรก
    else:
        form = StudentRegisterForm()  # ค่าเริ่มต้นเป็น student form
    return render(request, 'register.html', {'form': form})

# ฟังก์ชันสำหรับการเข้าสู่ระบบ
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)  # แบบฟอร์มล็อกอิน
        if form.is_valid():
            user = form.get_user()
            login(request, user)  # ล็อกอินผู้ใช้
            return redirect('index')  # กลับไปหน้าแรก
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# ฟังก์ชันสำหรับ admin เพิ่มกิจกรรม
@user_passes_test(is_admin)
def add_activity(request):
    if request.method == 'POST':
        name = request.POST.get('name')  # ชื่อกิจกรรม
        description = request.POST.get('description')  # คำอธิบายกิจกรรม
        date = request.POST.get('date')  # วันที่จัดกิจกรรม

        # ตรวจสอบว่าข้อมูลครบถ้วน
        if name and description and date:
            activity = Activity.objects.create(
                name=name,
                description=description,
                date=date,
                created_by=request.user
            )
            return redirect('index')  # กลับไปหน้าแรก
        else:
            return render(request, 'add_activity.html', {'error': 'กรุณากรอกข้อมูลให้ครบถ้วน'})
    return render(request, 'add_activity.html')

# ฟังก์ชันสำหรับนักเรียนเข้าร่วมกิจกรรม
@login_required
def join_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)  # ดึงกิจกรรมหรือคืนค่า 404
    if request.user.user_type == 'student':
        participation, created = Participation.objects.get_or_create(
            activity=activity,
            student=request.user,
        )
        if not participation.participated:  # ถ้ายังไม่ได้เข้าร่วม
            participation.participated = True
            participation.save()
        return redirect('activity_list')  # กลับไปที่รายการกิจกรรม
    return redirect('index')  # ถ้าไม่ใช่นักเรียนให้กลับไปหน้าแรก

# ฟังก์ชันแสดงรายการกิจกรรมทั้งหมด
@login_required
def activity_list(request):
    activities = Activity.objects.all()  # ดึงข้อมูลกิจกรรมทั้งหมด
    return render(request, 'activity_list.html', {'activities': activities})

# ฟังก์ชันแสดงรายงานการเข้าร่วมกิจกรรม
@user_passes_test(is_admin)
def participation_report(request):
    participations = Participation.objects.select_related('activity', 'student')  # ดึงข้อมูลการเข้าร่วม
    return render(request, 'participation_report.html', {'participations': participations})
