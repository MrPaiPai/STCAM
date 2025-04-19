from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter ที่ใช้ดึงค่าจาก dictionary
    ใช้งานใน template: {{ dict|get_item:key }}
    """
    return dictionary.get(str(key), 0)