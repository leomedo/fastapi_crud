import json

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from firebase_admin import firestore
from starlette.responses import JSONResponse

from firebase_init import db
from models import BookingRequest, UpdateRequest
from redis_config import redis_client
from utils import generate_daily_slots
from datetime import datetime
import uvicorn


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request, date: str = None):
    if not date:
        return templates.TemplateResponse("index.html",
                                          {"request": request, "slots": [], "date": "", "error": "يرجى اختيار التاريخ",
                                           "show_booked": False})
    # if not date:
    #     date = datetime.today().strftime("%Y-%m-%d")
    dt = datetime.strptime(date, "%Y-%m-%d")
    today = datetime.today().date()
    if dt.date() < today:
        return templates.TemplateResponse("index.html",
                                          {"request": request, "slots": [], "error": "لا يمكن الحجز في تاريخ ماضي",
                                           "date": date})
    if dt.weekday() in [4, 5]:
        return templates.TemplateResponse("index.html",
                                          {"request": request, "slots": [], "error": "الحجز غير متاح في هذا اليوم",
                                           "date": date})
    all_slots = generate_daily_slots()
    booked_doc = db.collection("appointments").document(date).get()
    booked_times = []
    if booked_doc.exists:
        for s in booked_doc.to_dict().get("slots", []):
            if not s.get("available", True):
                booked_times.append(s["time"])

    now_time = datetime.now().time()
    slots = []
    for slot in all_slots:
        slot_time = datetime.strptime(slot["time"], "%I:%M %p").time()
        if slot["time"] not in booked_times:
            if dt.date() == today and slot_time <= now_time:
                continue
            slots.append(slot)

    return templates.TemplateResponse("index.html", {"request": request, "slots": slots, "date": date})


@app.post("/book")
def book(req: BookingRequest):
    today = datetime.today().date()
    booking_date = datetime.strptime(req.date, "%Y-%m-%d").date()
    if booking_date < today:
        raise HTTPException(400, "لا يمكن الحجز في تاريخ قديم")
    if booking_date == today and datetime.strptime(req.time, "%I:%M %p").time() <= datetime.now().time():
        raise HTTPException(400, "لا يمكن الحجز في وقت قديم من اليوم")
    allowed_slots = [slot["time"] for slot in generate_daily_slots()]
    if req.time not in allowed_slots:
        raise HTTPException(400, detail="الوقت غير صالح، يجب اختيار وقت من المواعيد المحددة فقط")
    doc_ref = db.collection("appointments").document(req.date)
    doc = doc_ref.get()
    slots = []
    if doc.exists:
        slots = doc.to_dict().get("slots", [])
        for slot in slots:
            if slot["time"] == req.time and not slot["available"]:
                raise HTTPException(303, "هذا التوقيت محجوز من قبل")

    slots.append({
        "time": req.time,
        "available": False,
        "booked_by": req.booked_by.dict()
    })
    doc_ref.set({"slots": slots})
    return JSONResponse(content={"status": "done added"}, status_code=200)


@app.get("/show", response_class=HTMLResponse, include_in_schema=False)
async def show_booked_appointments(request: Request, date: str):
    cache_key = "appointments"
    cache_expire_time = 5
    cached_slots = redis_client.get(cache_key)
    if cached_slots:
        slots = json.loads(cached_slots)
    else:
        doc_ref = db.collection("appointments").document(date)
        doc = doc_ref.get()
        slots = doc.to_dict()["slots"] if doc.exists else []
        redis_client.set("appointments", json.dumps(slots), ex=cache_expire_time)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "slots": slots,
        "date": date,
        "error": None,
        "show_booked": True
    })


@app.get("/get_all_slot", response_class=HTMLResponse)
async def show_booked_appointments(date: str):
    cache_key = "appointments"
    cache_expire_time = 5
    cached_slots = redis_client.get(cache_key)
    if cached_slots:
        slots = json.loads(cached_slots)
    else:
        doc_ref = db.collection("appointments").document(date)
        doc = doc_ref.get()
        slots = doc.to_dict()["slots"] if doc.exists else []
        redis_client.set("appointments", json.dumps(slots), ex=cache_expire_time)
    return JSONResponse(content={
        "slots": slots,
        "date": date,
        "error": None,
    }, status_code=200)


@app.delete("/delete")
async def delete_booking(date: str = Query(...), time: str = Query(...)):
    doc_ref = db.collection("appointments").document(date)
    doc = doc_ref.get()
    if not doc.exists:
        return JSONResponse(content={"status": "not found"}, status_code=404)

    data = doc.to_dict()
    slots = data.get("slots", [])

    slot_to_delete = next((slot for slot in slots if slot["time"] == time), None)
    if not slot_to_delete:
        return JSONResponse(content={"status": "slot not found"}, status_code=404)

    doc_ref.update({
        "slots": firestore.ArrayRemove([slot_to_delete])
    })
    ########### Cach Delete ###########
    redis_client.delete("appointments")

    return JSONResponse(content={"status": "deleted"}, status_code=200)


@app.put("/update")
async def update_booking(data: UpdateRequest):
    doc_ref = db.collection("appointments").document(data.date)
    doc = doc_ref.get()
    if not doc.exists:
        return JSONResponse(content={"status": "not found"}, status_code=404)

    slots = doc.to_dict().get("slots", [])
    for slot in slots:
        if data.booked_by:
            print(data.booked_by.dict(exclude_unset=True))
            for key, value in data.booked_by.dict(exclude_unset=True).items():
                slot["booked_by"][key] = value
        break
    else:
        return JSONResponse(content={"status": "slot not found"}, status_code=404)
    doc_ref.update({"slots": slots})
    ########### Cach Delete ###########
    redis_client.delete("appointments")
    return JSONResponse(content={"status": "updated"}, status_code=200)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
