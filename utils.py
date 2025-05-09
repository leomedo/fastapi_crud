from datetime import datetime, timedelta

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
