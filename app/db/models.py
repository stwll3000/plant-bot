from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # Первичный ключ = Telegram user_id, отдельной авторизации нет
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    first_name: Mapped[str] = mapped_column(String(128))
    username: Mapped[str | None] = mapped_column(String(64))
    photo_file_id: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    invite_code: Mapped[str] = mapped_column(String(16), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "family_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    family_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("families.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(16), default="member")  # owner | member
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship()
    family: Mapped["Family"] = relationship()


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("families.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    rooms: Mapped[list["Room"]] = relationship(back_populates="property")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    property_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("properties.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(128))

    property: Mapped["Property"] = relationship(back_populates="rooms")
    plants: Mapped[list["Plant"]] = relationship(back_populates="room")


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rooms.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(128))
    species: Mapped[str | None] = mapped_column(String(128))
    photo_file_id: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    room: Mapped["Room"] = relationship(back_populates="plants")
    schedules: Mapped[list["PlantCareSchedule"]] = relationship(
        back_populates="plant"
    )


class CareType(Base):
    """Справочник типов ухода. В MVP только 'watering',
    подкормка/опрыскивание/пересадка добавятся строками, без миграций схемы."""

    __tablename__ = "care_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))


class PlantCareSchedule(Base):
    """Интервал и сроки ухода живут здесь, а не в plants —
    у растения может быть несколько расписаний (полив, подкормка...)."""

    __tablename__ = "plant_care_schedules"
    __table_args__ = (
        UniqueConstraint("plant_id", "care_type_id"),
        Index("ix_schedules_next_due_at", "next_due_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE")
    )
    care_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("care_types.id", ondelete="CASCADE")
    )
    interval_days: Mapped[int] = mapped_column(Integer)
    last_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    plant: Mapped["Plant"] = relationship(back_populates="schedules")
    care_type: Mapped["CareType"] = relationship()


class CareLog(Base):
    __tablename__ = "care_logs"
    __table_args__ = (Index("ix_care_logs_plant_done", "plant_id", "done_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plants.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    care_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("care_types.id"))
    done_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    note: Mapped[str | None] = mapped_column(Text)

    plant: Mapped["Plant"] = relationship()
    user: Mapped["User"] = relationship()
    care_type: Mapped["CareType"] = relationship()
