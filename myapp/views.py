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
    return render(request, 'index.html')

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

            return redirect('activity_list')
    else:
        activity_form = ActivityForm()
        formset = ImageFormSet(queryset=ActivityImage.objects.none())
    return render(request, 'add_activity.html', {'activity_form': activity_form, 'formset': formset})

# ฟังก์ชันสำหรับนักเรียนเข้าร่วมกิจกรรม
@login_required
def join_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    
    # ตรวจสอบว่าผู้ใช้เคยเข้าร่วมกิจกรรมนี้แล้วหรือไม่
    participation, created = Participation.objects.get_or_create(
        activity=activity,
        student=request.user  # ใช้ user ที่ล็อกอินอยู่
    )

    if created:
        messages.success(request, f"คุณได้เข้าร่วมกิจกรรม {activity.name} เรียบร้อยแล้ว!")
    else:
        messages.warning(request, f"คุณเคยเข้าร่วมกิจกรรม {activity.name} แล้ว")

    return redirect('activity_detail', activity_id=activity.id)


# ฟังก์ชันแสดงรายการกิจกรรมทั้งหมด
@login_required
def activity_list(request):
    if is_student(request.user):
        activities = Activity.objects.filter(participation__student=request.user).distinct()
    else:
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
    return render(request, 'upload_proof.html')

def index(request):
    activities = Activity.objects.all()  
    return render(request, 'index.html', {'activities': activities})


# ฟังก์ชันแสดงประกาศในหน้าแรก
def home(request):
    activities = Activity.objects.all()
    announcements = Announcement.objects.order_by('-created_at')  # เรียงจากใหม่ไปเก่า
    return render(request, 'index.html', {'activities': activities, 'announcements': announcements})

def activity_info(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)  # ดึงกิจกรรมที่ตรงกับ activity_id
    return render(request, 'activity_info.html', {'activity': activity})  # ส่งข้อมูลไปยังเทมเพลต

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
    user = request.user  # ดึงข้อมูลผู้ใช้ที่ล็อกอินอยู่

    # ดึงข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วม
    participations = Participation.objects.filter(student=user)
    activities = [participation.activity for participation in participations]

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('edit_userprofile')  # รีเฟรชหน้าหลังจากบันทึกสำเร็จ
    else:
        form = UserProfileForm(instance=user)

    # ส่งข้อมูล activities ไปยัง template
    return render(request, 'edit_userprofile.html', {
        'form': form,
        'user': user,
        'activities': activities  # ส่งข้อมูลกิจกรรมที่ผู้ใช้เข้าร่วม
    })



# อัพโหลดหลักฐานการเข้าร่วม
@login_required
def upload_proof(request):
    participations = Participation.objects.filter(
        student=request.user,
        status='approved'
    ).select_related('activity')

    print("Participations:", list(participations))

    if request.method == 'POST':
        try:
            activity_id = int(request.POST.get('activity_id', 0))
        except ValueError:
            activity_id = 0

        proof_image = request.FILES.get('proof_image')

        if activity_id and proof_image:
            activity = get_object_or_404(Activity, id=activity_id)

            registration, created = ActivityRegistration.objects.update_or_create(
                user=request.user,
                activity=activity,
                defaults={
                    'proof_image': proof_image,
                    'proof_upload_date': timezone.now(),  # ตรวจสอบและตั้งค่า proof_upload_date
                }
            )

            return redirect('user_upload_proof_list')

    registrations = [
        ActivityRegistration.objects.get_or_create(
            user=request.user,
            activity=participation.activity
        )[0]
        for participation in participations if participation.activity
    ]

    return render(request, 'upload_proof.html', {
        'registrations': registrations
    })

@login_required
def user_upload_proof_list(request):
    # ดึงข้อมูลการลงทะเบียนทั้งหมดของผู้ใช้ พร้อมข้อมูลกิจกรรมที่เกี่ยวข้อง
    registrations = ActivityRegistration.objects.filter(
        user=request.user
    ).select_related('activity')

    # Debug ข้อมูล
    for reg in registrations:
        print("=== Debug ข้อมูล ===")
        print(f"Registration ID: {reg.id}")
        print(f"Activity ID: {reg.activity_id}")
        print(f"Activity Name: {reg.activity.name if reg.activity else 'ไม่มีชื่อกิจกรรม'}")
        print(f"Image: {reg.proof_image}")
        print(f"Proof Upload Date: {reg.proof_upload_date}")
        print("-------------------")

    # ตรวจสอบและตั้งค่า proof_upload_date ถ้ายังไม่มี
    for reg in registrations:
        if reg.proof_upload_date is None:
            reg.proof_upload_date = timezone.now()
            reg.save()

    return render(request, 'user_upload_proof_list.html', {
        'registrations': registrations
    })


#ลบรูปหลักฐานการเข้าร่วม
@login_required
def delete_proof(request, reg_id):
    registration = get_object_or_404(ActivityRegistration, id=reg_id, user=request.user)
    
    # ลบไฟล์ภาพก่อน
    if registration.proof_image:
        registration.proof_image.delete(save=False)  # ลบจากระบบไฟล์
    
    # ลบข้อมูลออกจากฐานข้อมูล
    registration.delete()

    return redirect('user_upload_proof_list')  # กลับไปยังหน้ารายการหลักฐาน



# def add_announcement(request):
#     return render(request, 'add_announcement.html')

@login_required
def show_all_proofs(request):
    if is_student(request.user):
        registrations = ActivityRegistration.objects.filter(user=request.user).select_related('activity').order_by('-proof_upload_date')
    else:
        registrations = ActivityRegistration.objects.select_related('activity').order_by('-proof_upload_date')

    for reg in registrations:
        if reg.proof_upload_date is None:
            reg.proof_upload_date = timezone.now()
            reg.save()

    return render(request, 'show_all_proofs.html', {'registrations': registrations})



@user_passes_test(is_admin)
def manage_participations(request):
    participations = Participation.objects.select_related('activity', 'student').all()
    return render(request, 'manage_participation.html', {'participations': participations})

# เดิม: แสดงการเข้าร่วมเดี่ยว (เปลี่ยนชื่อให้ชัดเจน)
@user_passes_test(is_admin)
def manage_participation(request, participation_id=None):
    if participation_id:
        participation = get_object_or_404(Participation, id=participation_id)
        return render(request, 'manage_participation.html', {'participation': participation})
    else:
        return redirect('manage_participations')