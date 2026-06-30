# app/schemas/payment_schema.py
from pydantic import BaseModel, Field

class CreatePaymentIntentRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Monto en centavos (ej: 5000 = $50 MXN)")
    currency: str = Field(default="mxn")

class PaymentIntentResponse(BaseModel):
    clientSecret: str
    paymentIntentId: str