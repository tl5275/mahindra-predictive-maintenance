"""Simple vehicle summary model for backend bootstrapping and health checks."""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    health: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    rpm: Mapped[int] = mapped_column(Integer)
    battery: Mapped[float] = mapped_column(Float)
    anomaly_score: Mapped[float] = mapped_column(Float)
    rul_hours: Mapped[float] = mapped_column(Float)
