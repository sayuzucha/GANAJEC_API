# app/routes/payment_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.payment_schema import CreatePaymentIntentRequest, PaymentIntentResponse
from app.controllers.payment_controller import create_payment_intent, listar_planes
from app.core.deps import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/payments", tags=["Payments"])

@router.get("/planes")
def get_planes(db: Session = Depends(get_db)):
    return listar_planes(db)

@router.post("/create-intent", response_model=PaymentIntentResponse)
def create_intent(
    body: CreatePaymentIntentRequest,
    current_user = Depends(get_current_user)
):
    return create_payment_intent(body.amount, body.currency)