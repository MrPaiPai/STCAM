# Generated by Django 5.1.3 on 2025-02-16 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_participation_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participation',
            name='status',
            field=models.CharField(choices=[('pending', 'ยังไม่อนุมัติ'), ('approved', 'อนุมัติแล้ว'), ('rejected', 'ไม่อนุมัติ')], default='pending', max_length=10, verbose_name='สถานะการลงทะเบียน'),
        ),
    ]
