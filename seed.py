from models import *
from datetime import date, timedelta
import random

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Department).first():
        print("Already seeded.")
        db.close()
        return

    # --- Departments ---
    depts = [
        Department(name="Cardiology",    type="IPD", bed_capacity=40),
        Department(name="Orthopaedics",  type="IPD", bed_capacity=30),
        Department(name="Oncology",      type="IPD", bed_capacity=25),
        Department(name="Neurology",     type="IPD", bed_capacity=20),
        Department(name="General OPD",   type="OPD", bed_capacity=0),
        Department(name="Paediatrics",   type="OPD", bed_capacity=20),
        Department(name="ICU",           type="ICU", bed_capacity=20),
        Department(name="Maternity",     type="IPD", bed_capacity=25),
        Department(name="Dermatology",   type="OPD", bed_capacity=0),
        Department(name="Lab/Radiology", type="Lab", bed_capacity=0),
    ]
    db.add_all(depts)
    db.commit()

    dept_map = {d.name: d for d in db.query(Department).all()}

    # --- Staff ---
    roles_by_dept = {
        "Cardiology":    [("Doctor",3),("Nurse",8)],
        "Orthopaedics":  [("Doctor",2),("Nurse",6)],
        "Oncology":      [("Doctor",2),("Nurse",6)],
        "Neurology":     [("Doctor",2),("Nurse",5)],
        "General OPD":   [("Doctor",4),("Nurse",4),("Admin",3)],
        "Paediatrics":   [("Doctor",2),("Nurse",4)],
        "ICU":           [("Doctor",3),("Nurse",10)],
        "Maternity":     [("Doctor",2),("Nurse",6)],
        "Dermatology":   [("Doctor",1),("Nurse",2)],
        "Lab/Radiology": [("Lab",5)],
    }
    staff_list = []
    for dept_name, roles in roles_by_dept.items():
        for role, count in roles:
            for i in range(count):
                staff_list.append(Staff(name=f"{role}_{dept_name[:4]}_{i+1}", role=role, department_id=dept_map[dept_name].id))
    hk = [Staff(name=f"HK_{i}", role="Housekeeping", department_id=dept_map["General OPD"].id) for i in range(10)]
    staff_list.extend(hk)
    db.add_all(staff_list)
    db.commit()

    all_staff = db.query(Staff).all()

    # --- Attendance (last 30 days) ---
    attendance_rates = {"Doctor": 0.92, "Nurse": 0.96, "Admin": 0.89, "Lab": 0.82, "Housekeeping": 0.74}
    att_records = []
    for i in range(30):
        day = date.today() - timedelta(days=i)
        for s in all_staff:
            rate = attendance_rates.get(s.role, 0.90)
            att_records.append(Attendance(staff_id=s.id, date=day, present=1 if random.random() < rate else 0))
    db.add_all(att_records)

    # --- Patients (last 30 days) ---
    names = ["Ramesh Kumar","Priya Sharma","Arun Nair","Meena Iyer","Suresh Babu",
             "Lakshmi Devi","Vikram Singh","Anita Patel","Ravi Verma","Sunita Rao",
             "Karthik M","Deepa N","Sanjay G","Pooja T","Arjun K","Nisha V","Mohan D","Uma S"]
    patients = []
    for i in range(800):
        dept = random.choice([d for d in depts if d.type in ["OPD","IPD"]])
        adm = date.today() - timedelta(days=random.randint(0, 29))
        disc = adm + timedelta(days=random.randint(1,8)) if dept.type == "IPD" and random.random() > 0.3 else None
        wait = random.randint(8, 42) if dept.type == "OPD" else 0
        patients.append(Patient(
            name=random.choice(names),
            age=random.randint(18, 80),
            gender=random.choice(["M","F"]),
            type=dept.type,
            department_id=dept.id,
            admission_date=adm,
            discharge_date=disc,
            wait_time_minutes=wait,
            satisfaction_score=round(random.uniform(3.0, 5.0), 1),
            readmitted=1 if random.random() < 0.06 else 0,
            insurance_type=random.choice(["cash","insurance","corporate"]),
            bill_amount=round(random.uniform(2000, 180000), 2)
        ))
    db.add_all(patients)

    # --- Revenue Records (last 6 months) ---
    rev_data = {
        "Cardiology":    [132,138,145,139,148,155],
        "Orthopaedics":  [88,92,96,90,98,102],
        "Oncology":      [75,78,82,79,84,88],
        "Neurology":     [62,65,68,64,70,73],
        "General OPD":   [45,47,50,48,52,54],
        "Paediatrics":   [20,22,24,21,23,25],
        "ICU":           [35,38,40,37,42,44],
        "Maternity":     [28,30,32,29,33,35],
        "Dermatology":   [12,13,14,12,15,15],
        "Lab/Radiology": [23,25,27,24,28,29],
    }
    months = ["2025-12","2026-01","2026-02","2026-03","2026-04","2026-05"]
    rev_records = []
    for dept_name, amounts in rev_data.items():
        for i, month in enumerate(months):
            rev_records.append(RevenueRecord(
                department_id=dept_map[dept_name].id,
                month=month,
                amount=amounts[i],
                target=amounts[i] * random.uniform(0.95, 1.08)
            ))
    db.add_all(rev_records)

    # --- Bed Occupancy (last 30 days) ---
    occ_data = {
        "Cardiology":  (40, 0.82), "Orthopaedics": (30, 0.75),
        "Oncology":    (25, 0.70), "Neurology":    (20, 0.68),
        "ICU":         (20, 0.95), "Maternity":    (25, 0.65),
        "Paediatrics": (20, 0.72),
    }
    bed_records = []
    for i in range(30):
        day = date.today() - timedelta(days=i)
        for dname, (cap, rate) in occ_data.items():
            occ = int(cap * rate * random.uniform(0.92, 1.05))
            occ = min(occ, cap)
            bed_records.append(BedOccupancy(department_id=dept_map[dname].id, date=day, occupied=occ, capacity=cap))
    db.add_all(bed_records)

    # --- Daily Admissions (last 7 days) ---
    days_adm = []
    for i in range(7):
        day = date.today() - timedelta(days=i)
        days_adm.append(DailyAdmission(date=day, opd_count=random.randint(150,260), ipd_count=random.randint(28,62)))
    db.add_all(days_adm)

    # --- Alerts ---
    alerts = [
        Alert(severity="critical", title="ICU at 95% capacity", message="Only 1 bed available. High weekend admission load expected. Consider activating overflow protocol.", created_at=datetime.utcnow()),
        Alert(severity="warning",  title="Cardiology OPD wait spike", message="Wait time reached 34 min — 42% above 20-min target. Recommend opening second consultation counter.", created_at=datetime.utcnow() - timedelta(hours=2)),
        Alert(severity="warning",  title="Pending AR increased", message="Accounts receivable up ₹6L. 3 insurance claims pending >30 days. Escalate to billing team.", created_at=datetime.utcnow() - timedelta(days=1)),
        Alert(severity="success",  title="Revenue target on track", message="₹4.2Cr achieved with 5 days remaining. Projected to exceed monthly target by 6%.", created_at=datetime.utcnow()),
        Alert(severity="info",     title="Housekeeping attendance low", message="74% attendance this week — below 85% threshold. 3 staff on sick leave.", created_at=datetime.utcnow() - timedelta(hours=5)),
    ]
    db.add_all(alerts)
    db.commit()
    db.close()
    print("✅ Database seeded successfully!")

if __name__ == "__main__":
    seed()
