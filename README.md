# 🏥 Hospital CEO BI Dashboard
### XelerAIT Hackathon — Apollo Multispeciality Hospital

---

## Stack
| Layer | Tech |
|-------|------|
| Frontend | HTML + Chart.js (no framework needed) |
| Backend | Python FastAPI |
| Database | SQLite (via SQLAlchemy ORM) |
| AI Concierge | Anthropic Claude API (next step) |

---

## Project Structure
```
hospital-dashboard/
├── backend/
│   ├── main.py          ← FastAPI app + all API routes
│   ├── models.py        ← SQLAlchemy DB models (schema)
│   ├── seed.py          ← Dummy data generator
│   ├── requirements.txt
│   └── hospital.db      ← SQLite database (auto-created)
├── frontend/
│   └── index.html       ← Full dashboard UI
├── start.sh             ← One-click startup
└── README.md
```

---

## Quick Start
```bash
chmod +x start.sh
./start.sh
```
Then open `frontend/index.html` in your browser.

---

## Database Schema
- **departments** — 10 hospital departments (Cardiology, ICU, OPD, etc.)
- **patients** — 800 dummy patients with admission dates, bills, wait times
- **staff** — Doctors, Nurses, Admin, Lab, Housekeeping
- **attendance** — 30 days of daily attendance records
- **revenue_records** — 6 months revenue + targets per department
- **bed_occupancy** — 30 days of daily bed usage per ward
- **daily_admissions** — 7 days of OPD/IPD counts
- **alerts** — Smart alerts with severity levels

---

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kpis` | All 8 KPIs with trends |
| GET | `/api/revenue/trend` | 6-month revenue vs target |
| GET | `/api/beds/by-department` | Bed occupancy per ward |
| GET | `/api/admissions/daily` | Daily OPD/IPD counts |
| GET | `/api/revenue/by-department` | Dept-wise revenue split |
| GET | `/api/opd/wait-times` | Avg wait time per dept |
| GET | `/api/staff/attendance` | Attendance % by role |
| GET | `/api/alerts` | Active smart alerts |
| PATCH | `/api/alerts/:id/resolve` | Resolve an alert |

---

## KPIs Tracked
1. Monthly Revenue (₹) vs Target
2. Bed Occupancy Rate (%)
3. OPD Wait Time (minutes)
4. Patient Satisfaction Score (/5)
5. Readmission Rate (%)
6. Average Length of Stay (days)
7. OT Utilization (%)
8. Pending Accounts Receivable (₹)

---

## Next Steps (for hackathon)
- [ ] AI Concierge (Claude API) — NLP queries on dashboard
- [ ] Predictive Analytics — Bed forecast, revenue projection
- [ ] Department drill-down views
- [ ] Date range filter
- [ ] Export to PDF/Excel
