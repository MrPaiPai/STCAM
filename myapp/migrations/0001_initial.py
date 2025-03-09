# Generated by Django 5.1.3 on 2025-02-23 10:54

import datetime
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('user_type', models.CharField(choices=[('student', 'นักศึกษา'), ('teacher', 'อาจารย์'), ('admin', 'ผู้ดูแลระบบ')], default='student', max_length=10, verbose_name='ประเภทผู้ใช้')),
                ('student_id', models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='รหัสนักศึกษา')),
                ('year', models.IntegerField(blank=True, choices=[(1, 'ชั้นปีที่ 1'), (2, 'ชั้นปีที่ 2'), (3, 'ชั้นปีที่ 3'), (4, 'ชั้นปีที่ 4')], null=True, verbose_name='ชั้นปี')),
                ('branch', models.CharField(blank=True, choices=[('CS', 'วิทยาการคอมพิวเตอร์'), ('CCS', 'วิทยาศาสตร์เครื่องสำอาง'), ('OHS', 'อาชีวอนามัยและความปลอดภัย'), ('EHS', 'อนามัยสิ่งแวดล้อมและสาธารณภัย'), ('MS', 'วิทยาศาสตร์การแพทย์'), ('GS', 'วิทยาศาสตร์ทั่วไป'), ('IT', 'เทคโนโลยีสารสนเทศ'), ('BIB', 'อุตสาหกรรมชีวภาพเพื่อธุรกิจ'), ('CYB', 'ความมั่นคงปลอดภัยไซเบอร์')], max_length=255, null=True, verbose_name='สาขา')),
                ('groups', models.ManyToManyField(blank=True, related_name='customuser_groups', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='customuser_permissions', to='auth.permission')),
            ],
            options={
                'verbose_name': 'ผู้ใช้',
                'verbose_name_plural': 'ผู้ใช้ทั้งหมด',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='ชื่อกิจกรรม')),
                ('description', models.TextField(verbose_name='รายละเอียดกิจกรรม')),
                ('start_date', models.DateField(default=datetime.date.today, verbose_name='วันที่เริ่มจัดกิจกรรม')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='วันที่สิ้นสุดกิจกรรม')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='ผู้สร้างกิจกรรม')),
            ],
            options={
                'verbose_name': 'กิจกรรม',
                'verbose_name_plural': 'กิจกรรมทั้งหมด',
            },
        ),
        migrations.CreateModel(
            name='ActivityImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='activity_images/', verbose_name='รูปภาพ')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='myapp.activity', verbose_name='กิจกรรม')),
            ],
            options={
                'verbose_name': 'รูปภาพกิจกรรม',
                'verbose_name_plural': 'รูปภาพทั้งหมด',
            },
        ),
        migrations.CreateModel(
            name='ActivityRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registration_date', models.DateTimeField(auto_now_add=True)),
                ('proof_image', models.ImageField(blank=True, null=True, upload_to='proofs/')),
                ('proof_upload_date', models.DateTimeField(blank=True, null=True)),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.activity')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'การลงทะเบียนกิจกรรม',
                'verbose_name_plural': 'การลงทะเบียนกิจกรรมทั้งหมด',
                'ordering': ['-registration_date'],
            },
        ),
        migrations.CreateModel(
            name='MyUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('role', models.CharField(choices=[('user', 'User'), ('teacher', 'Teacher')], default='user', max_length=10)),
                ('groups', models.ManyToManyField(blank=True, related_name='myuser_groups', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='myuser_permissions', to='auth.permission')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Participation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('pending', 'ยังไม่อนุมัติ'), ('approved', 'อนุมัติแล้ว'), ('rejected', 'ไม่อนุมัติ')], default='pending', max_length=10, verbose_name='สถานะการลงทะเบียน')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.activity', verbose_name='กิจกรรม')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='นักศึกษา')),
            ],
            options={
                'verbose_name': 'การเข้าร่วมกิจกรรม',
                'verbose_name_plural': 'การเข้าร่วมกิจกรรมทั้งหมด',
                'unique_together': {('activity', 'student')},
            },
        ),
    ]
