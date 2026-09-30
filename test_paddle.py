import asyncio
import json

from app.services.paddle_service import paddle_service


async def main():
    print("=" * 60)
    print(" TEST DE CONEXIÓN CON PADDLE")
    print("=" * 60)

    print(f"Environment : {paddle_service.get_environment()}")
    print(f"Base URL    : {paddle_service.base_url}")

    # No mostramos la API Key por seguridad
    if paddle_service.api_key:
        print("API Key     : configurada")
    else:
        print("API Key     : NO CONFIGURADA")

    print("-" * 60)

    try:
        result = await paddle_service.test_connection()

        print("✅ CONEXIÓN EXITOSA")
        print("-" * 60)

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False,
            )
        )

    except Exception as e:
        print("❌ ERROR DE CONEXIÓN")
        print("-" * 60)
        print(f"Tipo de error: {type(e).__name__}")
        print(f"Detalle      : {e}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())