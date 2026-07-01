# app/models/payment.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=False)
    amount = Column(Integer, nullable=False)  # en centavos
    currency = Column(String(10), default="mxn")
    status = Column(String(50), default="pending")  # pending, succeeded, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())