import asyncio
import json

import httpx


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

BASE_URL = "https://api.fda.gov/drug/label.json"


# ==========================================================
# PRUEBA OPENFDA
# ==========================================================

async def main():

    print("=" * 70)
    print("MEDICAL AI - PRUEBA OPENFDA")
    print("=" * 70)

    query = "aspirin"

    print()
    print(f"Consulta: {query}")
    print(f"URL: {BASE_URL}")

    params = {
        "search": f'openfda.generic_name:"{query}"',
        "limit": 5,
    }

    try:

        print()
        print("[1/3] Conectando con openFDA...")

        async with httpx.AsyncClient(timeout=30.0) as client:

            response = await client.get(
                BASE_URL,
                params=params,
            )

            print(
                f"HTTP Status: {response.status_code}"
            )

            print(
                f"URL final: {response.url}"
            )

            # ==================================================
            # VALIDAR RESPUESTA
            # ==================================================

            if response.status_code != 200:

                print()
                print("❌ ERROR EN OPENFDA")
                print()
                print(response.text[:3000])

                return

            print()
            print("✓ Conexión con openFDA exitosa.")

            # ==================================================
            # JSON
            # ==================================================

            print()
            print("[2/3] Procesando respuesta JSON...")

            data = response.json()

            meta = data.get("meta", {})
            results = data.get("results", [])

            print()
            print(
                f"Total encontrado: "
                f"{meta.get('results', {}).get('total', len(results))}"
            )

            print(
                f"Resultados recibidos: {len(results)}"
            )

            # ==================================================
            # MOSTRAR RESULTADOS
            # ==================================================

            print()
            print("[3/3] Analizando resultados...")
            print("=" * 70)

            for index, result in enumerate(
                results,
                start=1
            ):

                print()
                print("-" * 70)
                print(f"[{index}]")

                openfda = result.get(
                    "openfda",
                    {}
                )

                print(
                    "ID:",
                    openfda.get(
                        "application_number",
                        ["N/A"]
                    )[0]
                    if openfda.get("application_number")
                    else "N/A"
                )

                print(
                    "Marca:",
                    openfda.get(
                        "brand_name",
                        ["N/A"]
                    )[0]
                    if openfda.get("brand_name")
                    else "N/A"
                )

                print(
                    "Genérico:",
                    openfda.get(
                        "generic_name",
                        ["N/A"]
                    )[0]
                    if openfda.get("generic_name")
                    else "N/A"
                )

                print(
                    "Fabricante:",
                    openfda.get(
                        "manufacturer_name",
                        ["N/A"]
                    )[0]
                    if openfda.get("manufacturer_name")
                    else "N/A"
                )

                # ==================================================
                # CAMPOS MÉDICOS IMPORTANTES
                # ==================================================

                for field in [
                    "indications_and_usage",
                    "warnings",
                    "contraindications",
                    "drug_interactions",
                    "adverse_reactions",
                    "dosage_and_administration",
                ]:

                    values = result.get(field)

                    if values:

                        print()
                        print(
                            f"{field.upper()}:"
                        )

                        if isinstance(values, list):

                            text = " ".join(
                                str(v)
                                for v in values
                            )

                        else:

                            text = str(values)

                        print(
                            text[:1000]
                        )

            # ==================================================
            # GUARDAR RESPUESTA COMPLETA
            # ==================================================

            output_file = (
                "scripts/test_output/"
                "openfda_response.json"
            )

            with open(
                output_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            print()
            print("=" * 70)
            print("RESPUESTA COMPLETA GUARDADA EN:")
            print(output_file)
            print("=" * 70)

            print()
            print(
                "✓ PRUEBA OPENFDA COMPLETADA"
            )

    except httpx.HTTPError as e:

        print()
        print("❌ ERROR HTTP:")
        print(e)

    except Exception as e:

        print()
        print("❌ ERROR:")
        print(e)


if __name__ == "__main__":

    asyncio.run(main())
