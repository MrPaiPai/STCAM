from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import StudentRegisterForm, AdminRegisterForm, ActivityForm, ActivityImageForm
from .models import Activity, ActivityImage, Participation
from django.forms import modelformset_factory
from .models import MyUser
from .forms import MyUserForm
from django.shortcuts import render
from django.urls import reverse
from django.shortcuts import redirect

def some_view(request):
    return redirect(reverse('home'))  # ใช้ชื่อ URL 'home' ที่กำหนดใน urls.py

# ฟังก์ชันตรวจสอบว่าเป็น admin หรือไม่
def is_admin(user):
    return user.user_type == 'admin'

# ฟังก์ชันสำหรับหน้าแรก
def index(request):
    return render(request, 'index.html')

# ฟังก์ชันสำหรับการลงทะเบียนผู้ใช้
def register(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'student'
            user.save()
            login(request, user)
            return redirect('home')
    else:
        form = StudentRegisterForm()
    return render(request, 'register.html', {'form': form})

# ฟังก์ชันสำหรับการเข้าสู่ระบบ
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

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

            return redirect('activity_list')
    else:
        activity_form = ActivityForm()
        formset = ImageFormSet(queryset=ActivityImage.objects.none())
    return render(request, 'add_activity.html', {'activity_form': activity_form, 'formset': formset})

# ฟังก์ชันสำหรับนักเรียนเข้าร่วมกิจกรรม
@login_required
def join_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    if request.user.user_type == 'student':
        # ตรวจสอบว่าผู้ใช้เข้าร่วมกิจกรรมแล้วหรือไม่
        participation, created = Participation.objects.get_or_create(
            activity=activity,
            student=request.user,
        )
        if not participation.participated:
            participation.participated = True
            participation.save()
        return redirect('activity_list')
    return redirect('index')

# ฟังก์ชันแสดงรายการกิจกรรมทั้งหมด
@login_required
def activity_list(request):
    activities = Activity.objects.all()
    return render(request, 'activity_list.html', {'activities': activities})

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

def activity_info(request):
    return render(request, 'activity_info.html')