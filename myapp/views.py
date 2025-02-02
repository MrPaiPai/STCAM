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
from .models import Announcement
from django.views.decorators.csrf import csrf_exempt  # ใช้ในกรณีที่ไม่ต้องการ CSRF error
from django.contrib import messages
from django.contrib.auth import logout


# views.py


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
            user.set_password(form.cleaned_data["password"])
            user.is_active = True  # ✅ ตั้งค่าให้ user สามารถใช้งานได้ทันที
            user.save()
            
            # ทำการ login หลังจากลงทะเบียนสำเร็จ
            user = authenticate(request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                return redirect('home')
    else:
        form = StudentRegisterForm()
    return render(request, 'register.html', {'form': form})

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

def track_participation(request):
    return render(request, 'track_participation.html')

def upload_proof(request):
    return render(request, 'upload_proof.html')

def index(request):
    activities = Activity.objects.all()  
    return render(request, 'index.html', {'activities': activities})



@csrf_exempt
def add_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title', 'ประกาศใหม่')  # ถ้าไม่กรอกจะใช้ "ประกาศใหม่"
        content = request.POST.get('announcement_text')

        if content:
            Announcement.objects.create(title=title, content=content)

        return redirect('/')  # กลับไปหน้าแรกหลังโพสต์

    return render(request, 'add_announcement.html')  # ถ้าหลุดมา GET, ให้แสดงฟอร์มเพิ่มประกาศ

def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'home.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)  # ดึงกิจกรรมที่ตรงกับ activity_id
    return render(request, 'activity_info.html', {'activity': activity})  # ส่งข้อมูลไปยังเทมเพลต

def logout_view(request):
    logout(request)
    return redirect('login')  # เปลี่ยนเส้นทางไปหน้า login

