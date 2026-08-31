import httpx

from typing import List, Optional

from app.schemas.medical import NormalizedDocument


class OpenFDAService:

    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    BASE_URL = "https://api.fda.gov/drug/label.json"

    # ==========================================================
    # BUSCAR MEDICAMENTOS
    # ==========================================================

    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 5
    ) -> List[NormalizedDocument]:
        """
        Consulta openFDA utilizando el nombre genérico del medicamento.

        Ejemplo:
            aspirin
            acetaminophen
            ibuprofen
        """

        if not query:
            return []

        params = {
            "search": f'openfda.generic_name:"{query}"',
            "limit": max_results,
        }

        print("==================================================")
        print("OPENFDA SEARCH")
        print(f"Query: {query}")
        print("==================================================")

        try:

            async with httpx.AsyncClient(
                timeout=30.0
            ) as client:

                response = await client.get(
                    self.BASE_URL,
                    params=params
                )

                response.raise_for_status()

                data = response.json()

            results = data.get("results", [])

            print(
                f"OpenFDA resultados encontrados: "
                f"{len(results)}"
            )

            normalized_docs = []

            for result in results:

                doc = self._parse_drug_label(
                    result
                )

                if doc:
                    normalized_docs.append(doc)

            print(
                f"OpenFDA documentos normalizados: "
                f"{len(normalized_docs)}"
            )

            return normalized_docs

        except httpx.HTTPStatusError as e:

            # --------------------------------------------------
            # openFDA devuelve 404 cuando no encuentra resultados
            # --------------------------------------------------

            if e.response.status_code == 404:

                print(
                    f"OpenFDA: no se encontraron "
                    f"resultados para '{query}'"
                )

                return []

            print(
                f"Error HTTP consultando OpenFDA: {e}"
            )

            return []

        except httpx.RequestError as e:

            print(
                f"Error de conexión con OpenFDA: {e}"
            )

            return []

        except Exception as e:

            print(
                f"Error procesando OpenFDA: {e}"
            )

            return []

    # ==========================================================
    # PARSEAR MEDICAMENTO
    # ==========================================================

    def _parse_drug_label(
        self,
        drug: dict
    ) -> Optional[NormalizedDocument]:
        """
        Convierte la estructura de openFDA a
        nuestro modelo NormalizedDocument.
        """

        try:

            # ==================================================
            # INFORMACIÓN OPENFDA
            # ==================================================

            openfda = drug.get(
                "openfda",
                {}
            )

            # ==================================================
            # ID DEL MEDICAMENTO
            # ==================================================

            set_id = drug.get(
                "set_id"
            )

            if not set_id:

                # Algunos registros pueden no traer
                # set_id, intentamos utilizar application_number

                application_numbers = (
                    openfda.get(
                        "application_number",
                        []
                    )
                )

                if application_numbers:

                    set_id = application_numbers[0]

            if not set_id:

                return None

            # ==================================================
            # NOMBRE DE MARCA
            # ==================================================

            brand_names = openfda.get(
                "brand_name",
                []
            )

            brand_name = (
                brand_names[0]
                if brand_names
                else ""
            )

            # ==================================================
            # NOMBRE GENÉRICO
            # ==================================================

            generic_names = openfda.get(
                "generic_name",
                []
            )

            generic_name = (
                generic_names[0]
                if generic_names
                else ""
            )

            # ==================================================
            # FABRICANTE
            # ==================================================

            manufacturers = openfda.get(
                "manufacturer_name",
                []
            )

            manufacturer = (
                manufacturers[0]
                if manufacturers
                else ""
            )

            # ==================================================
            # TÍTULO
            # ==================================================

            if brand_name and generic_name:

                title = (
                    f"{brand_name} "
                    f"({generic_name})"
                )

            elif generic_name:

                title = generic_name

            elif brand_name:

                title = brand_name

            else:

                title = "Medicamento sin nombre"

            # ==================================================
            # INDICACIONES
            # ==================================================

            indications = self._get_text(
                drug,
                "indications_and_usage"
            )

            # ==================================================
            # ADVERTENCIAS
            # ==================================================

            warnings = self._get_text(
                drug,
                "warnings"
            )

            # ==================================================
            # DOSIFICACIÓN
            # ==================================================

            dosage = self._get_text(
                drug,
                "dosage_and_administration"
            )

            # ==================================================
            # DESCRIPCIÓN
            # ==================================================

            description = self._get_text(
                drug,
                "description"
            )

            # ==================================================
            # ABSTRACT UNIFICADO
            # ==================================================

            abstract_parts = []

            if indications:

                abstract_parts.append(
                    f"Indications and Usage: "
                    f"{indications}"
                )

            if description:

                abstract_parts.append(
                    f"Description: "
                    f"{description}"
                )

            if warnings:

                abstract_parts.append(
                    f"Warnings: "
                    f"{warnings}"
                )

            if dosage:

                abstract_parts.append(
                    f"Dosage and Administration: "
                    f"{dosage}"
                )

            abstract = "\n\n".join(
                abstract_parts
            )

            if not abstract:

                abstract = (
                    "No hay información "
                    "clínica disponible."
                )

            # ==================================================
            # URL
            # ==================================================

            url = (
                f"https://api.fda.gov/drug/label.json"
                f"?search=set_id:{set_id}"
            )

            # ==================================================
            # METADATA
            # ==================================================

            metadata = {

                "source": "openFDA",

                "brand_name": brand_name,

                "generic_name": generic_name,

                "manufacturer": manufacturer,

                "indications_and_usage":
                    indications,

                "warnings":
                    warnings,

                "dosage_and_administration":
                    dosage,

                "description":
                    description,

                "route":
                    openfda.get(
                        "route",
                        []
                    ),

                "substance_name":
                    openfda.get(
                        "substance_name",
                        []
                    ),

                "product_type":
                    openfda.get(
                        "product_type",
                        []
                    ),

                "application_number":
                    openfda.get(
                        "application_number",
                        []
                    ),

                "raw_set_id":
                    set_id,
            }

            # ==================================================
            # DOCUMENTO NORMALIZADO
            # ==================================================

            return NormalizedDocument(

                source_id=str(
                    set_id
                ),

                source_type="openfda",

                title=title,

                abstract=abstract,

                authors=[
                    manufacturer
                ] if manufacturer else [],

                publication_date=None,

                url=url,

                metadata=metadata,
            )

        except Exception as e:

            print(
                f"Error procesando medicamento "
                f"de openFDA: {e}"
            )

            return None

    # ==========================================================
    # OBTENER TEXTO DE CAMPOS OPENFDA
    # ==========================================================

    @staticmethod
    def _get_text(
        drug: dict,
        field: str
    ) -> str:
        """
        openFDA normalmente devuelve estos campos
        como listas de strings.
        """

        value = drug.get(
            field,
            []
        )

        if not value:

            return ""

        if isinstance(
            value,
            list
        ):

            return " ".join(
                str(item)
                for item in value
                if item
            ).strip()

        return str(
            value
        ).strip()