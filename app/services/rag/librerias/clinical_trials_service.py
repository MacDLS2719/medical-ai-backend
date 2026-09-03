import httpx
from typing import List, Optional
from app.services.rag.schemas import NormalizedDocument


class ClinicalTrialsService:
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    async def search_and_fetch(self, query: str, max_results: int = 5) -> List[NormalizedDocument]:
        """Consulta la API v2 de ClinicalTrials.gov por condición/patología."""
        params = {
            "query.cond": query,
            "pageSize": max_results,
            "format": "json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            studies = data.get("studies", [])
            normalized_docs = []

            for study in studies:
                doc = self._parse_study(study)
                if doc:
                    normalized_docs.append(doc)

            return normalized_docs

    def _parse_study(self, study: dict) -> Optional[NormalizedDocument]:
        """Convierte la estructura del protocolo del ensayo al DTO unificado."""
        try:
            protocol = study.get("protocolSection", {})

            # ID (NCTId)
            nct_id = protocol.get("identificationModule", {}).get("nctId", "")
            if not nct_id:
                return None

            # Título
            title = protocol.get("identificationModule", {}).get("briefTitle", "Sin título")

            # Resumen/Descripción
            abstract = protocol.get("descriptionModule", {}).get("briefSummary", "Sin resumen disponible.")

            # Estado del ensayo clínico
            status = protocol.get("statusModule", {}).get("overallStatus", "UNKNOWN")

            # Fechas
            start_date_dict = protocol.get("statusModule", {}).get("startDateStruct", {})
            pub_date = start_date_dict.get("date", None)

            # Intervenciones (fármacos, terapias, etc.)
            interventions_raw = protocol.get("armsInterventionsModule", {}).get("interventions", [])
            interventions = [i.get("name", "") for i in interventions_raw if isinstance(i, dict) and i.get("name")]

            # Patrocinador principal (Sponsor)
            sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", "")
            authors = [f"Sponsor: {sponsor}"] if sponsor else []

            return NormalizedDocument(
                source_id=nct_id,
                source_type="clinical_trials",
                title=title,
                abstract=abstract,
                authors=authors,
                publication_date=pub_date,
                url=f"https://clinicaltrials.gov/study/{nct_id}",
                metadata={
                    "status": status,
                    "interventions": interventions
                }
            )
        except Exception as e:
            print(f"Error procesando ensayo de ClinicalTrials: {e}")
            return None
