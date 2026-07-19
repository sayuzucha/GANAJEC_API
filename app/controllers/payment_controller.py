# app/controllers/payment_controller.py
import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.plan import Plan

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(amount: int, currency: str):
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
        )
        return {
            "clientSecret": intent.client_secret,
            "paymentIntentId": intent.id,
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e.user_message))

def listar_planes(db: Session):
    planes = db.query(Plan).filter(Plan.activo == True).all()
    return {"planes": [p.to_dict() for p in planes]}