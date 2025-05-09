from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class BookedBy(BaseModel):
    name: str = Field(..., description="اسم الشخص الذي قام بالحجز",  max_length=50)
    email: EmailStr = Field(..., description="البريد الإلكتروني للشخص")
    company: str = Field(..., description="اسم الشركة (اختياري إذا لم يكن هناك شركة)")
    country: str = Field(..., description="الدولة التي ينتمي لها الشخص")
    whatsapp: str = Field(..., description="رقم الواتساب للتواصل")


class BookingRequest(BaseModel):
    date: str = Field(..., description="تاريخ الموعد بصيغة YYYY-MM-DD")
    time: str = Field(..., description="وقت الموعد بصيغة HH:MM (24 ساعة)")
    booked_by: BookedBy = Field(..., description="معلومات الشخص الذي قام بالحجز")


class UpdateRequest(BaseModel):
    date: str = Field(..., description="تاريخ الموعد المراد تعديله")
    time: str = Field(..., description="وقت الموعد المراد تعديله")
    booked_by: Optional[BookedBy] = Field(None, description="المعلومات المحدثة للشخص الذي قام بالحجز")
