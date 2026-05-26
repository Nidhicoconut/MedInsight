from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models import *
from datetime import date, timedelta
from pydantic import BaseModel
from typing import List, Optional
import os
import httpx

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

app = FastAPI(title="Hospital BI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── HELPERS ────────────────────────────────────────────────
def current_month(): return date.today().strftime("%Y-%m")
def last_month():
    d = date.today().replace(day=1) - timedelta(days=1)
    return d.strftime("%Y-%m")

# ─── KPI SUMMARY ────────────────────────────────────────────
@app.get("/api/kpis")
def get_kpis(db: Session = Depends(get_db)):
    cm = current_month()
    lm = last_month()

    # Revenue
    rev_cm = db.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.month == cm).scalar() or 0
    rev_lm = db.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.month == lm).scalar() or 1
    rev_target = db.query(func.sum(RevenueRecord.target)).filter(RevenueRecord.month == cm).scalar() or 1

    # Bed occupancy (today)
    today = date.today()
    occ = db.query(func.sum(BedOccupancy.occupied)).filter(BedOccupancy.date == today).scalar() or 0
    cap = db.query(func.sum(BedOccupancy.capacity)).filter(BedOccupancy.date == today).scalar() or 1
    occ_yesterday = db.query(func.sum(BedOccupancy.occupied)).filter(BedOccupancy.date == today - timedelta(days=1)).scalar() or 1
    cap_yesterday = db.query(func.sum(BedOccupancy.capacity)).filter(BedOccupancy.date == today - timedelta(days=1)).scalar() or 1

    # OPD wait time avg
    wait_cm = db.query(func.avg(Patient.wait_time_minutes)).filter(
        Patient.type == "OPD",
        Patient.admission_date >= date.today().replace(day=1)
    ).scalar() or 0

    # Patient satisfaction
    sat_cm = db.query(func.avg(Patient.satisfaction_score)).filter(
        Patient.admission_date >= date.today().replace(day=1),
        Patient.satisfaction_score != None
    ).scalar() or 0

    # Readmission rate
    total_patients = db.query(func.count(Patient.id)).filter(
        Patient.admission_date >= date.today().replace(day=1)
    ).scalar() or 1
    readmitted = db.query(func.count(Patient.id)).filter(
        Patient.admission_date >= date.today().replace(day=1),
        Patient.readmitted == 1
    ).scalar() or 0

    # Avg length of stay
    alos = db.query(
        func.avg(func.julianday(Patient.discharge_date) - func.julianday(Patient.admission_date))
    ).filter(Patient.discharge_date != None).scalar() or 0

    # Pending AR (bills without discharge = still admitted = pending)
    ar = db.query(func.sum(Patient.bill_amount)).filter(
        Patient.discharge_date == None,
        Patient.type == "IPD"
    ).scalar() or 0

    # OT utilization — approximate from Cardiology + Ortho + Oncology + Neuro occupancy vs capacity
    ot_depts = db.query(func.sum(BedOccupancy.occupied), func.sum(BedOccupancy.capacity)).filter(
        BedOccupancy.date == today
    ).first()
    ot_util = round((ot_depts[0] or 0) / (ot_depts[1] or 1) * 100, 1)

    bed_pct = round(occ / cap * 100, 1)
    bed_prev = round(occ_yesterday / cap_yesterday * 100, 1)

    return {
        "revenue": {
            "current": round(rev_cm / 100, 2),
            "last_month": round(rev_lm / 100, 2),
            "target": round(rev_target / 100, 2),
            "change_pct": round((rev_cm - rev_lm) / rev_lm * 100, 1),
            "unit": "Lakhs"
        },
        "bed_occupancy": {
            "current_pct": bed_pct,
            "prev_pct": bed_prev,
            "change_pct": round(bed_pct - bed_prev, 1),
            "occupied": int(occ),
            "capacity": int(cap)
        },
        "opd_wait_time": {
            "avg_minutes": round(wait_cm, 1),
            "target_minutes": 20
        },
        "patient_satisfaction": {
            "score": round(sat_cm, 2),
            "max": 5.0
        },
        "readmission_rate": {
            "rate_pct": round(readmitted / total_patients * 100, 2),
            "readmitted": readmitted,
            "total": total_patients
        },
        "avg_length_of_stay": {
            "days": round(alos, 1),
            "target_days": 4.5
        },
        "pending_ar": {
            "amount_lakhs": round(ar / 100000, 2)
        },
        "ot_utilization": {
            "pct": ot_util
        }
    }

# ─── REVENUE TREND ──────────────────────────────────────────
@app.get("/api/revenue/trend")
def revenue_trend(db: Session = Depends(get_db)):
    months = ["2025-12","2026-01","2026-02","2026-03","2026-04","2026-05"]
    result = []
    for m in months:
        amt  = db.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.month == m).scalar() or 0
        tgt  = db.query(func.sum(RevenueRecord.target)).filter(RevenueRecord.month == m).scalar() or 0
        result.append({"month": m, "revenue": round(amt / 100, 2), "target": round(tgt / 100, 2)})
    return result

# ─── BED OCCUPANCY BY DEPT ──────────────────────────────────
@app.get("/api/beds/by-department")
def beds_by_dept(db: Session = Depends(get_db)):
    today = date.today()
    rows = db.query(
        Department.name,
        BedOccupancy.occupied,
        BedOccupancy.capacity
    ).join(Department, BedOccupancy.department_id == Department.id)\
     .filter(BedOccupancy.date == today).all()
    return [{"dept": r[0], "occupied": r[1], "capacity": r[2],
             "pct": round(r[1] / r[2] * 100, 1) if r[2] else 0} for r in rows]

# ─── DAILY ADMISSIONS ───────────────────────────────────────
@app.get("/api/admissions/daily")
def daily_admissions(db: Session = Depends(get_db)):
    rows = db.query(DailyAdmission).order_by(DailyAdmission.date.asc()).limit(7).all()
    return [{"date": str(r.date), "opd": r.opd_count, "ipd": r.ipd_count} for r in rows]

# ─── REVENUE BY DEPT ────────────────────────────────────────
@app.get("/api/revenue/by-department")
def revenue_by_dept(db: Session = Depends(get_db)):
    cm = current_month()
    rows = db.query(Department.name, func.sum(RevenueRecord.amount))\
             .join(RevenueRecord, RevenueRecord.department_id == Department.id)\
             .filter(RevenueRecord.month == cm)\
             .group_by(Department.name).all()
    total = sum(r[1] for r in rows) or 1
    return [{"dept": r[0], "amount_lakhs": round(r[1] / 100, 1), "pct": round(r[1] / total * 100, 1)} for r in rows]

# ─── DEPT WAIT TIMES ────────────────────────────────────────
@app.get("/api/opd/wait-times")
def wait_times(db: Session = Depends(get_db)):
    rows = db.query(Department.name, func.avg(Patient.wait_time_minutes))\
             .join(Patient, Patient.department_id == Department.id)\
             .filter(Patient.type == "OPD", Patient.admission_date >= date.today().replace(day=1))\
             .group_by(Department.name)\
             .order_by(func.avg(Patient.wait_time_minutes).desc()).all()
    return [{"dept": r[0], "avg_wait": round(r[1], 1)} for r in rows if r[1]]

# ─── STAFF ATTENDANCE ───────────────────────────────────────
@app.get("/api/staff/attendance")
def staff_attendance(db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=7)
    rows = db.query(Staff.role, func.avg(Attendance.present))\
             .join(Attendance, Attendance.staff_id == Staff.id)\
             .filter(Attendance.date >= since)\
             .group_by(Staff.role).all()
    return [{"role": r[0], "attendance_pct": round(r[1] * 100, 1)} for r in rows]

# ─── ALERTS ─────────────────────────────────────────────────
@app.get("/api/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).filter(Alert.resolved == 0)\
               .order_by(Alert.created_at.desc()).all()
    return [{
        "id": a.id, "severity": a.severity, "title": a.title,
        "message": a.message, "created_at": str(a.created_at)
    } for a in alerts]

@app.patch("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.resolved = 1
        db.commit()
    return {"status": "resolved"}

# ─── DEPARTMENTS LIST ────────────────────────────────────────
@app.get("/api/departments")
def get_departments(db: Session = Depends(get_db)):
    depts = db.query(Department).all()
    return [{"id": d.id, "name": d.name, "type": d.type, "bed_capacity": d.bed_capacity} for d in depts]

# ─── CHAT / RAG ──────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

def build_hospital_context(db: Session) -> str:
    """Pull live data from SQLite and format as context for the LLM."""
    today = date.today()
    cm = today.strftime("%Y-%m")
    lm = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    # Revenue
    rev_cm  = db.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.month == cm).scalar() or 0
    rev_lm  = db.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.month == lm).scalar() or 1
    rev_tgt = db.query(func.sum(RevenueRecord.target)).filter(RevenueRecord.month == cm).scalar() or 1

    # Bed occupancy
    occ = db.query(func.sum(BedOccupancy.occupied)).filter(BedOccupancy.date == today).scalar() or 0
    cap = db.query(func.sum(BedOccupancy.capacity)).filter(BedOccupancy.date == today).scalar() or 1

    # Per-department bed
    bed_rows = db.query(Department.name, BedOccupancy.occupied, BedOccupancy.capacity)\
                 .join(Department, BedOccupancy.department_id == Department.id)\
                 .filter(BedOccupancy.date == today).all()
    bed_str = ", ".join(f"{r[0]}: {r[1]}/{r[2]} ({round(r[1]/r[2]*100)}%)" for r in bed_rows)

    # OPD wait times
    wait_rows = db.query(Department.name, func.avg(Patient.wait_time_minutes))\
                  .join(Patient, Patient.department_id == Department.id)\
                  .filter(Patient.type == "OPD", Patient.admission_date >= today.replace(day=1))\
                  .group_by(Department.name).all()
    wait_str = ", ".join(f"{r[0]}: {round(r[1],1)}min" for r in wait_rows if r[1])

    # Satisfaction
    sat = db.query(func.avg(Patient.satisfaction_score))\
            .filter(Patient.admission_date >= today.replace(day=1)).scalar() or 0

    # Readmission
    total_p = db.query(func.count(Patient.id)).filter(Patient.admission_date >= today.replace(day=1)).scalar() or 1
    readm   = db.query(func.count(Patient.id)).filter(Patient.admission_date >= today.replace(day=1), Patient.readmitted == 1).scalar() or 0

    # ALOS
    alos = db.query(func.avg(func.julianday(Patient.discharge_date) - func.julianday(Patient.admission_date)))\
             .filter(Patient.discharge_date != None).scalar() or 0

    # Pending AR
    ar = db.query(func.sum(Patient.bill_amount)).filter(Patient.discharge_date == None, Patient.type == "IPD").scalar() or 0

    # Staff attendance (last 7 days)
    since = today - timedelta(days=7)
    staff_rows = db.query(Staff.role, func.avg(Attendance.present))\
                   .join(Attendance, Attendance.staff_id == Staff.id)\
                   .filter(Attendance.date >= since).group_by(Staff.role).all()
    staff_str = ", ".join(f"{r[0]}: {round(r[1]*100,1)}%" for r in staff_rows)

    # Department revenue this month
    dept_rev = db.query(Department.name, func.sum(RevenueRecord.amount))\
                 .join(RevenueRecord, RevenueRecord.department_id == Department.id)\
                 .filter(RevenueRecord.month == cm).group_by(Department.name)\
                 .order_by(func.sum(RevenueRecord.amount).desc()).all()
    dept_rev_str = ", ".join(f"{r[0]}: ₹{round(r[1]/100,1)}L" for r in dept_rev)

    # Revenue trend (last 6 months)
    months = ["2025-12","2026-01","2026-02","2026-03","2026-04","2026-05"]
    rev_trend = []
    for m in months:
        a = db.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.month == m).scalar() or 0
        t = db.query(func.sum(RevenueRecord.target)).filter(RevenueRecord.month == m).scalar() or 0
        rev_trend.append(f"{m}: ₹{round(a/100,1)}L (target ₹{round(t/100,1)}L)")
    rev_trend_str = " | ".join(rev_trend)

    # Active alerts
    alerts = db.query(Alert).filter(Alert.resolved == 0).order_by(Alert.created_at.desc()).all()
    alert_str = " | ".join(f"[{a.severity.upper()}] {a.title}: {a.message}" for a in alerts) or "No active alerts"

    # Daily admissions (last 7 days)
    adm_rows = db.query(DailyAdmission).order_by(DailyAdmission.date.desc()).limit(7).all()
    adm_str = ", ".join(f"{r.date}: OPD={r.opd_count} IPD={r.ipd_count}" for r in adm_rows)

    context = f"""
=== APOLLO MULTISPECIALITY HOSPITAL — LIVE DATA SNAPSHOT ({today}) ===

FINANCIAL KPIs:
- Monthly Revenue (current month {cm}): ₹{round(rev_cm/100,1)}L vs Target ₹{round(rev_tgt/100,1)}L ({round(rev_cm/rev_tgt*100,1)}% of target)
- Last Month Revenue ({lm}): ₹{round(rev_lm/100,1)}L
- Month-on-Month Change: {round((rev_cm-rev_lm)/rev_lm*100,1)}%
- Revenue by Department: {dept_rev_str}
- 6-Month Revenue Trend: {rev_trend_str}
- Pending Accounts Receivable (AR): ₹{round(ar/100000,2)}L (active IPD unpaid)

OPERATIONAL KPIs:
- Bed Occupancy: {occ}/{cap} beds ({round(occ/cap*100,1)}%) — Target: <85%
- Bed Occupancy by Department: {bed_str}
- OPD Average Wait Time by Department: {wait_str}
- Average Length of Stay (ALOS): {round(alos,1)} days — Target: 4.5 days
- OT Utilization (proxy): {round(occ/cap*100,1)}%

CLINICAL QUALITY KPIs:
- Patient Satisfaction Score: {round(sat,2)}/5.0 (this month)
- Readmission Rate: {readm}/{total_p} patients = {round(readm/total_p*100,2)}% — Target: <7%

STAFF KPIs (last 7 days attendance):
- {staff_str}

DAILY ADMISSIONS (last 7 days):
- {adm_str}

ACTIVE ALERTS:
- {alert_str}
"""
    return context.strip()

@app.post("/api/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not GROQ_API_KEY:
        return JSONResponse(status_code=500, content={"error": "GROQ_API_KEY not set. Run: export GROQ_API_KEY=your_key"})

    # Build live context from DB
    context = build_hospital_context(db)

    system_prompt = f"""You are an AI Concierge for Apollo Multispeciality Hospital, assisting the CEO.
You have access to live hospital data below. Use it to answer questions with specific numbers, trends, and actionable recommendations.

Rules:
- Always cite specific numbers from the data
- When a KPI is concerning, explain the likely root cause and recommend an action
- If asked about something not in the data, say "I don't have data on that right now" — never make up numbers
- Keep answers concise and executive-friendly (3-5 sentences max unless a detailed breakdown is asked)
- Use ₹ for Indian Rupees and Indian hospital context (NABH, CGHS, Ayushman Bharat, etc.)

{context}"""

    # Build message history for multi-turn
    messages = []
    for m in (req.history or []):
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "system", "content": system_prompt}] + messages,
                    "max_tokens": 512,
                    "temperature": 0.4
                }
            )
        data = resp.json()
        if "choices" not in data:
            return JSONResponse(status_code=500, content={"error": data.get("error", {}).get("message", "Groq API error")})
        reply = data["choices"][0]["message"]["content"]
        return {"reply": reply}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ─── HEALTH CHECK ────────────────────────────────────────────
@app.get("/health")
def health(): return {"status": "ok"}
