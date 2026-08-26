"""
Script de prueba para el nuevo servicio de traducción híbrido
"""
import asyncio
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.translation_service import TranslationService
from app.core.config import settings


async def test_translation():
    """Prueba básica del servicio de traducción"""

    print("=" * 50)
    print("PRUEBA DEL SERVICIO DE TRADUCCIÓN")
    print("=" * 50)
    print(f"Servicio configurado: {settings.TRANSLATION_SERVICE}")
    print(f"Usar traducción local: {settings.USE_LOCAL_TRANSLATION}")
    print(f"DeepL API Key configurada: {'Sí' if settings.DEEPL_API_KEY else 'No'}")
    print(f"Google API Key configurada: {'Sí' if settings.GOOGLE_TRANSLATE_API_KEY else 'No'}")
    print("=" * 50)

    # Crear instancia del servicio
    translation_service = TranslationService()

    # Textos de prueba
    test_cases = [
        ("Hello, this is a medical test.", "en", "es"),
        ("Artificial intelligence in medicine", "en", "es"),
        ("Patient with diabetes and hypertension", "en", "es"),
    ]

    for text, source, target in test_cases:
        print(f"\n--- Traduciendo: '{text}' ({source} -> {target}) ---")

        try:
            result = await translation_service.translate(
                text=text,
                source=source,
                target=target
            )
            print(f"Resultado: '{result}'")

            if result == text:
                print("⚠️  No se tradujo (se devolvió el original)")
            else:
                print("✅ Traducción exitosa")

        except Exception as e:
            print(f"❌ Error: {e}")

    # Prueba de consulta boolean
    print("\n" + "=" * 50)
    print("PRUEBA DE TRADUCCIÓN DE CONSULTA BOOLEAN")
    print("=" * 50)

    boolean_query = "(diabetes OR hypertension) AND treatment"
    print(f"Consulta original: '{boolean_query}'")

    try:
        translated_query = await translation_service.translate_query(
            text=boolean_query,
            source="en",
            target="es"
        )
        print(f"Consulta traducida: '{translated_query}'")
        print("✅ Traducción de consulta exitosa")

    except Exception as e:
        print(f"❌ Error en traducción de consulta: {e}")

    print("\n" + "=" * 50)
    print("PRUEBA COMPLETADA")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_translation())