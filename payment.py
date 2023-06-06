import os
import stripe

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')

def create_checkout_session(amount, currency, success_url, cancel_url):
    stripe.api_key = STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': currency,
                'product_data': {
                    'name': 'My Product',
                },
                'unit_amount': amount,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return session
