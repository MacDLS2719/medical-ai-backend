import asyncio
import os
import sys


# ==========================================================
# AGREGAR LA RAÍZ DEL PROYECTO AL PATH
# ==========================================================

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


from app.services.openfda_service import OpenFDAService


# ==========================================================
# TEST
# ==========================================================

async def main():

    print("=" * 70)
    print("MEDICAL AI - TEST OPENFDA SERVICE")
    print("=" * 70)

    query = "aspirin"

    print()
    print(f"Consulta: {query}")
    print()

    # ======================================================
    # CREAR SERVICIO
    # ======================================================

    service = OpenFDAService()

    # ======================================================
    # REALIZAR BÚSQUEDA
    # ======================================================

    try:

        results = await service.search_and_fetch(
            query=query,
            max_results=5
        )

    except Exception as e:

        print()
        print("❌ ERROR EJECUTANDO EL SERVICIO")
        print(e)
        return

    # ======================================================
    # RESULTADOS
    # ======================================================

    print()
    print("=" * 70)
    print(
        f"RESULTADOS ENCONTRADOS: {len(results)}"
    )
    print("=" * 70)

    if not results:

        print()
        print(
            "⚠️ No se encontraron resultados."
        )
        return

    # ======================================================
    # MOSTRAR RESULTADOS
    # ======================================================

    for index, doc in enumerate(
        results,
        start=1
    ):

        print()
        print("-" * 70)
        print(f"[{index}]")
        print("-" * 70)

        print(
            f"ID: {doc.source_id}"
        )

        print(
            f"TIPO: {doc.source_type}"
        )

        print(
            f"TÍTULO: {doc.title}"
        )

        print(
            f"FECHA: {doc.publication_date}"
        )

        print(
            f"URL: {doc.url}"
        )

        print()

        print(
            "ABSTRACT:"
        )

        print(
            doc.abstract[:1000]
            if doc.abstract
            else "Sin información"
        )

        print()

        print(
            "METADATA:"
        )

        print(
            doc.metadata
        )

    # ======================================================
    # VALIDACIONES
    # ======================================================

    print()
    print("=" * 70)
    print("VALIDACIONES")
    print("=" * 70)

    valid_documents = 0

    for doc in results:

        if (
            doc.source_id
            and doc.source_type == "openfda"
            and doc.title
            and doc.abstract
            and doc.url
            and isinstance(
                doc.metadata,
                dict
            )
        ):

            valid_documents += 1

    print()
    print(
        f"Documentos válidos: "
        f"{valid_documents}/{len(results)}"
    )

    if valid_documents == len(results):

        print()
        print(
            "✓ Todos los documentos "
            "fueron normalizados correctamente."
        )

    else:

        print()
        print(
            "⚠️ Algunos documentos "
            "presentan información incompleta."
        )

    print()
    print("=" * 70)
    print("TEST OPENFDA SERVICE COMPLETADO")
    print("=" * 70)


# ==========================================================
# EJECUTAR
# ==========================================================

if __name__ == "__main__":

    asyncio.run(main())
