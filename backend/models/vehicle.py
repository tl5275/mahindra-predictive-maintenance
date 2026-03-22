"""Simple vehicle summary model for backend bootstrapping and health checks."""

from sqlalchemy import Column, Float, Integer, String

from backend.db.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True)
    health = Column(Float)
    temperature = Column(Float)
    rpm = Column(Integer)
    battery = Column(Float)
    anomaly_score = Column(Float)
    rul_hours = Column(Float)
