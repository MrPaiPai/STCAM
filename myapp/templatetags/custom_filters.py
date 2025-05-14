from django import template

register = template.Library()

@register.filter
def get_participation(activity, user):
    """
    ใช้สำหรับดึงข้อมูลการลงทะเบียนกิจกรรมของผู้ใช้
    """
    return activity.participation_set.filter(student=user).first()

@register.filter
def get_item(dictionary, key):
    """
    ใช้สำหรับดึงค่าจาก dictionary ด้วย key
    """
    return dictionary.get(key)