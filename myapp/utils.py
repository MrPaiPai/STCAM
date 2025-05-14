from .models import SystemLog

def create_log(request, action, description, obj=None, module=None, status=None):
    """
    ฟังก์ชันสำหรับบันทึก Log ทำหน้าที่:
    1. บันทึกการกระทำต่างๆ ในระบบ
    2. เก็บข้อมูลผู้ใช้ที่ทำรายการ
    3. เก็บ IP Address และ User Agent
    4. เชื่อมโยงกับข้อมูลที่เกี่ยวข้อง (ถ้ามี)
    """
    try:
        log = SystemLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            description=description,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            module=module or '',
            status=status or ''
        )

        if obj:
            log.content_type = ContentType.objects.get_for_model(obj)
            log.object_id = obj.id
            log.save()

    except Exception as e:
        print(f"Error creating log: {e}")

def get_client_ip(request):
    """ฟังก์ชันสำหรับดึง IP Address ของผู้ใช้"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip