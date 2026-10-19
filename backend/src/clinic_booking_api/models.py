from datetime import UTC, date, datetime, time
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, String, text
from sqlalchemy.schema import SchemaItem
from sqlmodel import Field, SQLModel


class RecordBase(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )


class Clinic(RecordBase, table=True):
    __tablename__: ClassVar[str] = "clinic"  # pyright: ignore[reportIncompatibleVariableOverride]

    name: str
    timezone: str


class Doctor(RecordBase, table=True):
    __tablename__: ClassVar[str] = "doctor" # pyright: ignore[reportIncompatibleVariableOverride]


    clinic_id: UUID = Field(foreign_key="clinic.id")
    name: str
    specialty: str
    is_active: bool = True


class DoctorWorkingHour(RecordBase, table=True):
    __tablename__: ClassVar[str] = "doctor_working_hour" # pyright: ignore[reportIncompatibleVariableOverride]

    __table_args__: ClassVar[tuple[SchemaItem, ...]] = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_working_hour_weekday"),
        CheckConstraint(
            "start_time < end_time",
            name="ck_working_hour_time_order",
        ),
        Index("ix_working_hour_doctor_weekday", "doctor_id", "weekday"),
    )

    doctor_id: UUID = Field(foreign_key="doctor.id")
    weekday: int
    start_time: time
    end_time: time


class DoctorTimeOut(RecordBase, table=True):
    __tablename__: ClassVar[str] = "doctor_time_out" # pyright: ignore[reportIncompatibleVariableOverride]

    __table_args__: ClassVar[tuple[SchemaItem, ...]] = (
        CheckConstraint(
            "starts_at < ends_at",
            name="ck_doctor_time_out_time_order",
        ),
        Index("ix_doctor_time_out_doctor_starts_at", "doctor_id", "starts_at"),
    )

    doctor_id: UUID = Field(foreign_key="doctor.id")
    starts_at: datetime = Field(sa_type=DateTime(timezone=True))
    ends_at: datetime = Field(sa_type=DateTime(timezone=True))
    reason: str | None = None


class Patient(RecordBase, table=True):
    __tablename__: ClassVar[str] = "patient" # pyright: ignore[reportIncompatibleVariableOverride]

    full_name: str
    date_of_birth: date
    email: str
    phone: str


class AppUser(RecordBase, table=True):
    __tablename__:ClassVar[str] = "app_user" # pyright: ignore[reportIncompatibleVariableOverride]
    __table_args__: ClassVar[tuple[SchemaItem, ...]] = (
        CheckConstraint(
            """(role = 'patient' AND patient_id IS NOT NULL AND doctor_id IS NULL)
            OR (role = 'doctor' AND doctor_id IS NOT NULL AND patient_id IS NULL)
            OR (role = 'staff' AND patient_id IS NULL AND doctor_id IS NULL)""",
            name="ck_app_user_role_links",
        ),
    )

    email: str = Field(sa_type=String(), unique=True, index=True)
    password_hash: str
    role: str
    patient_id: UUID | None = Field(
        default=None,
        foreign_key="patient.id",
        unique=True,
    )
    doctor_id: UUID | None = Field(
        default=None,
        foreign_key="doctor.id",
        unique=True,
    )
    is_active: bool = True


class Appointment(RecordBase, table=True):
    __tablename__: ClassVar[str] = "appointment" # pyright: ignore[reportIncompatibleVariableOverride]

    __table_args__: ClassVar[tuple[SchemaItem, ...]] = (
        CheckConstraint(
            "status IN ('booked', 'cancelled', 'completed')",
            name="ck_appointment_status",
        ),
        Index(
            "uq_appointment_active_doctor_start",
            "doctor_id",
            "start_at",
            unique=True,
            postgresql_where=text("status = 'booked' AND deleted_at IS NULL"),
        ),
        Index("ix_appointment_patient_start_at", "patient_id", "start_at"),
    )

    doctor_id: UUID = Field(foreign_key="doctor.id")
    patient_id: UUID = Field(foreign_key="patient.id")
    start_at: datetime = Field(sa_type=DateTime(timezone=True))
    status: str = Field(default="booked", max_length=10)
    cancellation_reason: str | None = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )
    cancelled_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
