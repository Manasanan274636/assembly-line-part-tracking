# ไฟล์นี้คือ "เครื่องมือตรวจบัตรผ่าน" (Decorators)
# ทำไมถึงมีไฟล์นี้? -> เพื่อสร้างคำสั่งพิเศษ (เช่น @role_required) เอาไว้ใช้กำกับแต่ละหน้าเว็บว่าใครเข้าได้บ้าง
# มีหน้าที่สำคัญ:
# - เช็คหน้าที่ (Role) ของผู้ใช้งานที่กำลัง Login อยู่
# - ถ้าคนพยายามเข้าหน้า Admin แต่เป็น Operator ระบบจะสั่ง "Access Denied" (403) ทันที
# ที่เขียนแบบนี้เพื่อให้เราคุมความปลอดภัยของแต่ละหน้าได้ง่ายๆ แค่แปะป้ายกำกับไว้บนหัวฟังก์ชันครับ

# app/utils/decorators.py
from flask_login import current_user
from flask import abort
from functools import wraps


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
