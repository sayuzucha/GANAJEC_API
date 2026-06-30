# app/routes/payment_routes.py
from fastapi import APIRouter, Depends
from app.schemas.payment_schema import CreatePaymentIntentRequest, PaymentIntentResponse
from app.controllers.payment_controller import create_payment_intent
from app.core.deps import get_current_user

router = APIRouter(prefix="/api/payments", tags=["Payments"])

@router.post("/create-intent", response_model=PaymentIntentResponse)
def create_intent(
    body: CreatePaymentIntentRequest,
    current_user = Depends(get_current_user)  # protegido con JWT
):
    return create_payment_intent(body.amount, body.currency)