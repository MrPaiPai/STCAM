from django.shortcuts import redirect
from django.utils.timezone import now
from datetime import datetime, timedelta

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ตรวจสอบว่าผู้ใช้ล็อกอินอยู่หรือไม่
        if request.user.is_authenticated:
            current_time = now()
            # ตรวจสอบเวลาล่าสุดที่มีการใช้งาน
            if 'last_activity' in request.session:
                last_activity = datetime.fromisoformat(request.session['last_activity'])
                # ถ้าไม่มีการใช้งานเกิน 30 นาที
                if (current_time - last_activity) > timedelta(seconds=1800):
                    del request.session['last_activity']
                    return redirect('session_expired')
            # อัพเดทเวลาล่าสุดที่มีการใช้งาน
            request.session['last_activity'] = current_time.isoformat()
        
        response = self.get_response(request)
        return response