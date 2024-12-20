from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import StudentRegisterForm, AdminRegisterForm, ActivityForm
from .models import Activity, ActivityImage, Participation
from django.forms import modelformset_factory
from .forms import ActivityForm, ActivityImageForm

# ฟังก์ชันตรวจสอบว่าเป็น admin หรือไม่
def is_admin(user):
    return user.user_type == 'admin'

# ฟังก์ชันสำหรับหน้าแรก
def index(request):
    return render(request, 'index.html')  # หน้าแรก

# ฟังก์ชันสำหรับการลงทะเบียนผู้ใช้
def register(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'student'  # กำหนด user_type เป็น student
            user.save()
            login(request, user)
            return redirect('index')
    else:
        form = StudentRegisterForm()
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
        activity_form = ActivityForm(request.POST)
        images = request.FILES.getlist('images')  # รับรูปภาพหลายรูป
        if activity_form.is_valid():
            activity = activity_form.save(commit=False)
            activity.created_by = request.user  # เพิ่มผู้สร้าง
            activity.save()

            # บันทึกรูปภาพที่อัปโหลด
            for image in images:
                ActivityImage.objects.create(activity=activity, image=image)

            return redirect('activity_list')  # กลับไปที่หน้ารายการกิจกรรม
        else:
            return render(request, 'add_activity.html', {'activity_form': activity_form, 'error': 'กรุณากรอกข้อมูลให้ถูกต้อง'})
    else:
        activity_form = ActivityForm()
    return render(request, 'add_activity.html', {'activity_form': activity_form})

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

@login_required
def my_activities(request):
    activities = Participation.objects.filter(student=request.user)
    return render(request, 'my_activities.html', {'activities': activities})

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

            return redirect('index')
    else:
        activity_form = ActivityForm()
        formset = ImageFormSet(queryset=ActivityImage.objects.none())
    return render(request, 'add_activity.html', {'activity_form': activity_form, 'formset': formset})