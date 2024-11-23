from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from .forms import StudentRegisterForm, AdminRegisterForm
from .models import Activity, Participation
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin(user):
    return user.user_type == 'admin'

def index(request):
    return render(request, 'index.html')  # หน้าแรก

def register(request):
    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        if user_type == 'student':
            form = StudentRegisterForm(request.POST)
        else:
            form = AdminRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = user_type
            user.save()
            login(request, user)
            return redirect('index')
    else:
        form = StudentRegisterForm()  # Default to student form
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@user_passes_test(is_admin)
def add_activity(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        date = request.POST.get('date')
        activity = Activity.objects.create(
            name=name,
            description=description,
            date=date,
            created_by=request.user
        )
        return redirect('index')
    return render(request, 'add_activity.html')

@login_required
def participation_report(request):
    participations = Participation.objects.all()
    return render(request, 'participation_report.html', {'participations': participations})
