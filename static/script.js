async function submitBooking(e) {
    e.preventDefault();

    const form = e.target;
    const data = {
        date: form.date.value,
        time: form.time.value,
        booked_by: {
            name: form.name.value,
            email: form.email.value,
            company: form.company.value,
            country: form.country.value,
            whatsapp: form.whatsapp.value
        }
    };

    const res = await fetch("/book", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await res.json();
    if (result.status === "done added") {
        alert("تم الحجز بنجاح");
        location.reload();
    } else {
        alert("فشل الحجز");
    }
}
async function deleteSlot(e, date, time) {
    e.preventDefault();
    if (!confirm("هل أنت متأكد أنك تريد حذف الموعد؟")) return false;

    try {
        const response = await fetch(`/delete?date=${date}&time=${encodeURIComponent(time)}`, {
            method: "DELETE",
        });

        const result = await response.json();
        if (result.status === "deleted") {
            alert("تم حذف الموعد بنجاح");
            location.reload();
        } else {
            alert("فشل في الحذف: " + result.status);
        }
    } catch (error) {
        alert("حدث خطأ أثناء الحذف");
        console.error(error);
    }
    return false;
}

async function updateSlot(e, date, time, form) {
    e.preventDefault();

    const payload = {
        date: date,
        time: time,
        booked_by: {
            name: form.name.value,
            email: form.email.value,
            company: form.company.value,
            country: form.country.value,
            whatsapp: form.whatsapp.value
        }
    };

    try {
        const response = await fetch(`/update`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (result.status === "updated") {
            alert("تم تعديل الموعد بنجاح");
            location.reload();
        } else {
            alert("فشل في التعديل: " + result.status);
        }
    } catch (error) {
        alert("حدث خطأ أثناء التعديل");
        console.error(error);
    }

    return false;
}