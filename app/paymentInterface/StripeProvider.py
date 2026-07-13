import stripe

from PaymentProvider import PaymentProvider
from app import core
from cryptography.fernet import Fernet
cipher = Fernet(core.config.ENCRYPTION_KEY)
class StripePayment(PaymentProvider):
    def __init__(self, api_key):
        self.api_key = api_key
    def checkout(self, invoice, clinic):
        stripe.api_key = cipher.decrypt(clinic.payment_api_key).decode()
        session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Invoice {invoice.id}',
                        },
                        'unit_amount': int(invoice.amount * 100),  # amount in cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{core.config.FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{core.config.FRONTEND_URL}/cancel",
            )
        return session.url