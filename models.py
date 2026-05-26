from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./hospital.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    type = Column(String)  # OPD, IPD, ICU, OT, Lab
    bed_capacity = Column(Integer, default=0)
    patients = relationship("Patient", back_populates="department")
    staff = relationship("Staff", back_populates="department")
    revenue_records = relationship("RevenueRecord", back_populates="department")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    type = Column(String)  # OPD, IPD
    department_id = Column(Integer, ForeignKey("departments.id"))
    admission_date = Column(Date)
    discharge_date = Column(Date, nullable=True)
    wait_time_minutes = Column(Integer, default=0)
    satisfaction_score = Column(Float, nullable=True)
    readmitted = Column(Integer, default=0)
    insurance_type = Column(String, default="cash")  # cash, insurance
    bill_amount = Column(Float, default=0)
    department = relationship("Department", back_populates="patients")

class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    role = Column(String)  # Doctor, Nurse, Admin, Lab, Housekeeping
    department_id = Column(Integer, ForeignKey("departments.id"))
    department = relationship("Department", back_populates="staff")

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    staff_id = Column(Integer, ForeignKey("staff.id"))
    date = Column(Date)
    present = Column(Integer, default=1)

class RevenueRecord(Base):
    __tablename__ = "revenue_records"
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    month = Column(String)  # "2026-05"
    amount = Column(Float)
    target = Column(Float)
    department = relationship("Department", back_populates="revenue_records")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    severity = Column(String)  # critical, warning, info, success
    title = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Integer, default=0)

class BedOccupancy(Base):
    __tablename__ = "bed_occupancy"
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    date = Column(Date)
    occupied = Column(Integer)
    capacity = Column(Integer)

class DailyAdmission(Base):
    __tablename__ = "daily_admissions"
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    opd_count = Column(Integer, default=0)
    ipd_count = Column(Integer, default=0)
