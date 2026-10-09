import asyncio
import os
import stripe
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
price_id = os.getenv("STRIPE_DOCTOR_PRICE_ID")

async def main():
    print("=" * 60)
    print(" TEST DE CONEXIÓN CON STRIPE")
    print("=" * 60)

    print(f"Secret Key : {'configurada (Live/Test)' if stripe.api_key else 'NO CONFIGURADA'}")
    print(f"Price ID   : {price_id or 'NO CONFIGURADO'}")
    print("-" * 60)

    try:
        # Recuperar información de la cuenta de Stripe
        account = stripe.Account.retrieve()
        
        print("✅ CONEXIÓN EXITOSA CON STRIPE")
        print("-" * 60)
        print(f"ID de Cuenta : {account.id}")
        print(f"País         : {account.country}")
        print(f"Email        : {account.email}")

        # Validar si el Price ID del doctor existe en Stripe
        if price_id:
            try:
                price = stripe.Price.retrieve(price_id)
                amount_value = price.unit_amount / 100 if price.unit_amount else 0
                print(f"✅ Price ID Válido : {price.id} ({amount_value} {price.currency.upper()})")
            except Exception as price_err:
                print(f"⚠️ Advertencia con el Price ID: {price_err}")

    except Exception as e:
        print("❌ ERROR DE CONEXIÓN CON STRIPE")
        print("-" * 60)
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Detalle      : {e}")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())