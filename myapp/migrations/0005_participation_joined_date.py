# Generated by Django 5.1.7 on 2025-04-20 23:10

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_activity_faculty'),
    ]

    operations = [
        migrations.AddField(
            model_name='participation',
            name='joined_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='วันที่เข้าร่วม'),
            preserve_default=False,
        ),
    ]
