from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from functools import wraps
from time import time
from redis_config import REQUEST_LIMIT, TIME_WINDOW, redis_client


START_HOUR = 9
END_HOUR = 17
SLOT_DURATION = 30


def generate_daily_slots():
    slots = []
    start = datetime.strptime("09:00 AM", "%I:%M %p")
    end = datetime.strptime("05:00 PM", "%I:%M %p")
    while start < end:
        display_time = start.strftime("%I:%M %p")
        slots.append({
            "time": display_time,
            "available": True,
            "booked_by": None
        })
        start += timedelta(minutes=SLOT_DURATION)
    return slots


def rate_limit(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        ip_address = request.client.host
        current_time = int(time())
        key = f"rate_limit:{ip_address}"
        
        # تسجيل الطلب الحالي في Redis
        redis_client.zadd(key, {current_time: current_time})
        
        # إزالة الطلبات القديمة التي كانت قبل أكثر من دقيقة
        redis_client.zremrangebyscore(key, 0, current_time - TIME_WINDOW)
        
        # التحقق من عدد الطلبات في الدقيقة الأخيرة
        request_count = redis_client.zcard(key)
        
        if request_count > REQUEST_LIMIT:
            raise HTTPException(status_code=429, detail="عدد الطلبات المسموح بها تم تجاوزه. يرجى المحاولة لاحقًا.")
    
        return await func(request, *args, **kwargs) 
    return wrapper