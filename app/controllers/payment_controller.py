# app/controllers/payment_controller.py
import stripe
from fastapi import HTTPException
from app.core.config import settings  # asumiendo que tienes Settings con pydantic

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