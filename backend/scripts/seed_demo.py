import asyncio
import os
from datetime import UTC, date, datetime, time, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from pwdlib import PasswordHash
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from clinic_booking_api.db import engine, session_factory
from clinic_booking_api.models import (
    Appointment,
    AppUser,
    Clinic,
    Doctor,
    DoctorTimeOut,
    DoctorWorkingHour,
    Patient,
)

CLINIC_ID = uuid5(NAMESPACE_URL, "clinic-booking-demo:clinic")
CLINIC_TIMEZONE = ZoneInfo("Africa/Nairobi")
DOCTOR_DETAILS = (
    ("Amina Otieno", "General Practice"),
    ("Brian Mwangi", "Pediatrics"),
    ("Cynthia Wanjiku", "Family Medicine"),
    ("David Kiptoo", "Dermatology"),
    ("Esther Njeri", "General Practice"),
)


def demo_id(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"clinic-booking-demo:{key}")


def next_weekdays(start: date, count: int) -> list[date]:
    days: list[date] = []
    current = start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def appointment_in_utc(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=CLINIC_TIMEZONE).astimezone(UTC)


async def add_account(
    session: AsyncSession,
    password_hasher: PasswordHash,
    password: str,
    *,
    email: str,
    role: str,
    patient_id: UUID | None = None,
    doctor_id: UUID | None = None,
) -> None:
    account_id = demo_id(f"account:{email}")
    account = await session.get(AppUser, account_id)
    if account is not None:
        return

    existing = (await session.exec(select(AppUser).where(AppUser.email == email))).first()
    if existing is not None:
        raise ValueError(f"Seed account email is already used by another account: {email}")

    session.add(
        AppUser(
            id=account_id,
            email=email,
            password_hash=password_hasher.hash(password),
            role=role,
            patient_id=patient_id,
            doctor_id=doctor_id,
        )
    )


async def seed_demo() -> None:
    password = os.environ.get("DEMO_SEED_PASSWORD")
    if password is None or len(password) < 12:
        raise ValueError("Set DEMO_SEED_PASSWORD to a value of at least 12 characters")

    password_hasher = PasswordHash.recommended()
    try:
        async with session_factory() as session, session.begin():
            clinic = await session.get(Clinic, CLINIC_ID)
            if clinic is None:
                clinic = Clinic(
                    id=CLINIC_ID,
                    name="Savannah Demo Clinic",
                    timezone="Africa/Nairobi",
                )
                session.add(clinic)
                await session.flush()

            doctors: list[Doctor] = []
            for index, (name, specialty) in enumerate(DOCTOR_DETAILS, start=1):
                doctor_id = demo_id(f"doctor:{index}")
                doctor = await session.get(Doctor, doctor_id)
                if doctor is None:
                    doctor = Doctor(
                        id=doctor_id,
                        clinic_id=CLINIC_ID,
                        name=name,
                        specialty=specialty,
                    )
                    session.add(doctor)
                    await session.flush()
                doctors.append(doctor)

                await add_account(
                    session,
                    password_hasher,
                    password,
                    email=f"doctor{index:02}@example.test",
                    role="doctor",
                    doctor_id=doctor_id,
                )

                for weekday in range(5):
                    for shift, (start_time, end_time) in enumerate(
                        ((time(9), time(12)), (time(13), time(17))),
                        start=1,
                    ):
                        schedule_id = demo_id(
                            f"working-hour:{index}:{weekday}:{shift}"
                        )
                        if await session.get(DoctorWorkingHour, schedule_id) is None:
                            session.add(
                                DoctorWorkingHour(
                                    id=schedule_id,
                                    doctor_id=doctor_id,
                                    weekday=weekday,
                                    start_time=start_time,
                                    end_time=end_time,
                                )
                            )

            patients: list[Patient] = []
            for index in range(1, 41):
                patient_id = demo_id(f"patient:{index}")
                patient = await session.get(Patient, patient_id)
                if patient is None:
                    patient = Patient(
                        id=patient_id,
                        full_name=f"Demo Patient {index:02}",
                        date_of_birth=date(
                            1980 + index % 25,
                            1 + index % 12,
                            1 + index % 27,
                        ),
                        email=f"patient{index:02}@example.test",
                        phone=f"+254700{index:06}",
                    )
                    session.add(patient)
                    await session.flush()
                patients.append(patient)

                await add_account(
                    session,
                    password_hasher,
                    password,
                    email=f"patient{index:02}@example.test",
                    role="patient",
                    patient_id=patient_id,
                )

            await add_account(
                session,
                password_hasher,
                password,
                email="staff@example.test",
                role="staff",
            )

            upcoming_days = next_weekdays(
                datetime.now(CLINIC_TIMEZONE).date() + timedelta(days=1),
                4,
            )
            for index in range(20):
                appointment_id = demo_id(f"appointment:upcoming:{index + 1}")
                if await session.get(Appointment, appointment_id) is None:
                    doctor_index = index % len(doctors)
                    day_index = index // len(doctors)
                    session.add(
                        Appointment(
                            id=appointment_id,
                            doctor_id=doctors[doctor_index].id,
                            patient_id=patients[index].id,
                            start_at=appointment_in_utc(
                                upcoming_days[day_index],
                                time(
                                    9 + doctor_index // 2,
                                    30 * (doctor_index % 2),
                                ),
                            ),
                            status="booked",
                        )
                    )

            past_days = next_weekdays(
                datetime.now(CLINIC_TIMEZONE).date() - timedelta(days=14),
                5,
            )
            for index in range(4):
                appointment_id = demo_id(f"appointment:history:{index + 1}")
                if await session.get(Appointment, appointment_id) is None:
                    status = "completed" if index < 2 else "cancelled"
                    session.add(
                        Appointment(
                            id=appointment_id,
                            doctor_id=doctors[index].id,
                            patient_id=patients[20 + index].id,
                            start_at=appointment_in_utc(
                                past_days[index],
                                time(10, 0),
                            ),
                            status=status,
                            cancellation_reason=(
                                "Demo cancellation"
                                if status == "cancelled"
                                else None
                            ),
                            cancelled_at=(
                                appointment_in_utc(
                                    past_days[index],
                                    time(8, 0),
                                )
                                if status == "cancelled"
                                else None
                            ),
                        )
                    )

            for index, doctor in enumerate(doctors[:2], start=1):
                timeout_id = demo_id(f"time-out:{index}")
                if await session.get(DoctorTimeOut, timeout_id) is None:
                    session.add(
                        DoctorTimeOut(
                            id=timeout_id,
                            doctor_id=doctor.id,
                            starts_at=appointment_in_utc(
                                upcoming_days[3],
                                time(14, 0),
                            ),
                            ends_at=appointment_in_utc(
                                upcoming_days[3],
                                time(15, 0),
                            ),
                            reason="Demo time off",
                        )
                    )

    finally:
        await engine.dispose()

    print("Demo seed complete: 1 clinic, 5 doctors, 40 patients, and 1 staff account.")
    print("All demo accounts use the password provided in DEMO_SEED_PASSWORD.")


if __name__ == "__main__":
    asyncio.run(seed_demo())
