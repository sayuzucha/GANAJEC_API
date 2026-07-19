# app/schemas/payment_schema.py
from pydantic import BaseModel, Field


class CreatePaymentIntentRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Monto en centavos (ej: 5000 = $50 MXN)")
    currency: str = Field(default="mxn")


class PaymentIntentResponse(BaseModel):
    clientSecret: str
    paymentIntentId: str


class ConfirmarSuscripcionRequest(BaseModel):
    payment_intent_id: str = Field(..., description="ID del PaymentIntent de Stripe")
    plan_id: str = Field(..., description="ID del plan adquirido")
    monto: int = Field(..., gt=0, description="Monto pagado en centavos")
    moneda: str = Field(default="mxn")
    tipo_suscripcion: str = Field(default="mensual", description="mensual o anual")