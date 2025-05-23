# Generated by Django 5.1.7 on 2025-03-12 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_alter_activityregistration_proof_upload_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='faculty',
            field=models.CharField(choices=[('all', 'ทุกคนเข้าร่วมได้'), ('CS', 'วิทยาการคอมพิวเตอร์'), ('CCS', 'วิทยาศาสตร์เครื่องสำอาง'), ('OHS', 'อาชีวอนามัยและความปลอดภัย'), ('EHS', 'อนามัยสิ่งแวดล้อมและสาธารณภัย'), ('MS', 'วิทยาศาสตร์การแพทย์'), ('GS', 'วิทยาศาสตร์ทั่วไป'), ('IT', 'เทคโนโลยีสารสนเทศ'), ('BIB', 'อุตสาหกรรมชีวภาพเพื่อธุรกิจ'), ('CYB', 'ความมั่นคงปลอดภัยไซเบอร์')], default='all', max_length=10, verbose_name='คณะที่จัดกิจกรรม'),
        ),
    ]
