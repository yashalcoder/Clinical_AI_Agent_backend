#1. Admin clinic create karta hai
#2. Country pucho → Stripe ya JazzCash select
#3. Clinic apni API secret key deta hai → encrypted store hoti hai DB mein
#4. Patient appointment book karta hai → invoice ban jati hai (unpaid)
#5. Patient "Pay" click karta hai
#6. Backend: clinic ki stored key nikalta hai → Stripe ko call karta hai → checkout URL milta hai
#7. Patient Stripe pe redirect hota hai, wahan pay karta hai
#8. Stripe webhook backend ko batata hai "paid" → TAB invoice update hoti hai (client se nahi)
#9. Frontend sirf webhook ke baad wala status poll/check karta hai, khud set nahi karta

import stripe
from fastapi import HTTPException
from app.database import db
from app.models import Clinic
from cryptography.fernet import Fernet

from server.app import core
cipher = Fernet(core.config.ENCRYPTION_KEY)
class PaymentProvider:
    def __init__(self, name):
        self.name = name

    def save_credentials(self, clinic, api_key):
        encrypted_key = cipher.encrypt(api_key.encode())
        db.query(Clinic).filter(Clinic.id == clinic.id).update({
            "payment_provider": self.name,
            "payment_api_key": encrypted_key
        })
        db.commit()


    # Inside your class/service:
    def checkout(self, invoice, clinic):
        pass
    def verify_webhook(self, payload, signature):
            pass