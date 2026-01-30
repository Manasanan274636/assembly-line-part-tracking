# ไฟล์นี้เหมือน "สารบัญ" ของ Models ครับ เอาไว้รวบรวมไฟล์ Model ทั้งหมดให้เรียกใช้งานได้ง่ายๆ ในที่เดียว
# ทำไมถึงมีไฟล์นี้? -> เพื่อให้โค้ดส่วนอื่น (เช่น Routes หรือ Database Setup) สามารถเขียนรวบยอดแค่ `from app.models import ...` ได้เลย ไม่ต้องวิ่งไปเรียกทีละไฟล์
# มีหน้าที่สำคัญ:
# - รวมทุก Class (User, Part, Station, etc.) มาไว้เป็นก้อนเดียว
# - ช่วยให้ Flask-Migrate มองเห็นตารางทั้งหมดเวลาเราจะสร้างฐานข้อมูลใหม่ครับ

from app.models.user import User
from app.models.part import Part
from app.models.station import Station
from app.models.production_plan import ProductionPlan
from app.models.bom import BOM
from app.models.consumption import Consumption
from app.models.stock import Stock
