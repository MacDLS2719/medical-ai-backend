import asyncio
from pathlib import Path

import httpx


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

BASE_URL = "https://trialsearch.who.int"

SEARCH_URL = f"{BASE_URL}/Default.aspx"

QUERY = "leukemia"

OUTPUT_DIR = Path("scripts/test_output")


# ==========================================================
# TEST WHO ICTRP
# ==========================================================

async def test_who_ictrp():

    print("=" * 70)
    print("MEDICAL AI - PRUEBA DE BÚSQUEDA WHO ICTRP")
    print("=" * 70)

    print(f"\nConsulta: {QUERY}")
    print(f"URL: {SEARCH_URL}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Medical-AI/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        ) as client:

            # ==================================================
            # 1. ABRIR EL PORTAL
            # ==================================================

            print("\n[1/3] Abriendo portal WHO ICTRP...")

            response = await client.get(
                SEARCH_URL
            )

            print(
                f"HTTP Status: {response.status_code}"
            )

            print(
                f"URL final: {response.url}"
            )

            response.raise_for_status()

            # ==================================================
            # 2. GUARDAR PÁGINA INICIAL
            # ==================================================

            initial_file = (
                OUTPUT_DIR
                / "who_ictrp_search_page.html"
            )

            initial_file.write_text(
                response.text,
                encoding="utf-8"
            )

            print(
                f"Página inicial guardada en:"
                f"\n{initial_file}"
            )

            # ==================================================
            # 3. REALIZAR BÚSQUEDA
            # ==================================================

            print(
                "\n[2/3] Enviando búsqueda..."
            )

            # --------------------------------------------------
            # IMPORTANTE
            #
            # WHO ICTRP utiliza un formulario ASP.NET.
            #
            # Primero enviamos la consulta al formulario.
            # --------------------------------------------------

            data = {
                "ctl00$ContentPlaceHolder1$txtSearch": QUERY,
                "ctl00$ContentPlaceHolder1$btnSearch": "Search",
            }

            search_response = await client.post(
                SEARCH_URL,
                data=data
            )

            print(
                "HTTP Status búsqueda:",
                search_response.status_code
            )

            print(
                "URL final búsqueda:",
                search_response.url
            )

            search_response.raise_for_status()

            # ==================================================
            # GUARDAR RESULTADO
            # ==================================================

            result_file = (
                OUTPUT_DIR
                / "who_ictrp_search_result.html"
            )

            result_file.write_text(
                search_response.text,
                encoding="utf-8"
            )

            print(
                f"\nResultado guardado en:"
                f"\n{result_file}"
            )

            # ==================================================
            # COMPROBAR CONTENIDO
            # ==================================================

            content = search_response.text

            print(
                "\nTamaño respuesta:",
                len(content),
                "caracteres"
            )

            print(
                "\nPrimeros 2000 caracteres:"
            )

            print("-" * 70)

            print(
                content[:2000]
            )

            print("-" * 70)

            # ==================================================
            # BUSCAR INDICIOS DE RESULTADOS
            # ==================================================

            print(
                "\n[3/3] Analizando respuesta..."
            )

            indicators = [
                "Search Results",
                "TrialID",
                "Trial",
                "leukemia",
                "XML",
                "Export",
            ]

            found = []

            content_lower = content.lower()

            for indicator in indicators:

                if indicator.lower() in content_lower:

                    found.append(
                        indicator
                    )

            if found:

                print(
                    "\nIndicadores encontrados:"
                )

                for item in found:

                    print(
                        f"  ✓ {item}"
                    )

            else:

                print(
                    "\n⚠️ No se encontraron "
                    "indicadores conocidos."
                )

            # ==================================================
            # FINAL
            # ==================================================

            print("\n" + "=" * 70)
            print(
                "PRUEBA DE BÚSQUEDA COMPLETADA"
            )
            print("=" * 70)

            print(
                "\nArchivos generados:"
            )

            print(
                f"  1. {initial_file}"
            )

            print(
                f"  2. {result_file}"
            )

    except httpx.HTTPStatusError as e:

        print(
            "\n❌ ERROR HTTP"
        )

        print(
            f"Status: {e.response.status_code}"
        )

        print(
            f"URL: {e.response.url}"
        )

        print(
            "\nRespuesta:"
        )

        print(
            e.response.text[:3000]
        )

    except httpx.RequestError as e:

        print(
            "\n❌ ERROR DE CONEXIÓN"
        )

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

    except Exception as e:

        print(
            "\n❌ ERROR INESPERADO"
        )

        print(
            type(e).__name__
        )

        print(
            str(e)
        )


# ==========================================================
# EJECUCIÓN
# ==========================================================

if __name__ == "__main__":

    asyncio.run(
        test_who_ictrp()
    )