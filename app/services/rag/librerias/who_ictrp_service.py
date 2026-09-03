import httpx
from typing import List, Optional
from app.services.rag.schemas import NormalizedDocument

class WHOICTRPService:
    BASE_URL = "https://trialsearch.who.int/api/v2/trials"

    def __init__(self):
        self.api_key = ""  # WHO ICTRP no requiere API key para uso básico

    async def search_and_fetch(self, query: str, max_results: int = 5) -> List[NormalizedDocument]:
        """
        Busca ensayos clínicos en WHO ICTRP y retorna documentos normalizados.
        WHO ICTRP (International Clinical Trials Registry Platform) es la plataforma
        de la OMS para registros de ensayos clínicos de todo el mundo.
        """
        params = {
            "q": query,
            "pageSize": max_results,
            "format": "json"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

                trials = data.get("trials", [])
                
                # Manejo robusto si trials no es una lista
                if not isinstance(trials, list):
                    print(f"WHO ICTRP devolvió formato inesperado: {type(trials)}")
                    trials = []

                normalized_docs = []

                for trial in trials:
                    if isinstance(trial, dict):
                        doc = self._parse_trial(trial)
                        if doc:
                            normalized_docs.append(doc)

                print(f"WHO ICTRP: {len(normalized_docs)} documentos normalizados de {len(trials)} resultados")
                return normalized_docs

        except Exception as e:
            print(f"Error en WHO ICTRP search: {e}")
            return []

    def _parse_trial(self, trial: dict) -> Optional[NormalizedDocument]:
        """Procesa un ensayo clínico de WHO ICTRP al formato normalizado."""
        try:
            # ID del ensayo
            trial_id = trial.get("id", "") if trial else ""
            if not trial_id or not isinstance(trial_id, str):
                return None

            # Título - normalizar
            title = trial.get("public_title", "") if trial else ""
            if not title or not isinstance(title, str):
                title = "Sin título"
            else:
                title = title.strip() if title.strip() else "Sin título"

            # Resumen/Descripción - normalizar
            abstract = trial.get("scientific_title", "") if trial else ""
            if not abstract or not isinstance(abstract, str):
                abstract = trial.get("brief_summary", "") if trial else ""
            
            if not abstract or not isinstance(abstract, str):
                abstract = "Sin resumen disponible."
            else:
                abstract = abstract.strip() if abstract.strip() else "Sin resumen disponible."

            # Estado del ensayo - normalizar
            status = trial.get("primary_status", "Unknown") if trial else "Unknown"
            if not isinstance(status, str):
                status = "Unknown"

            # Fecha de registro - normalizar
            registration_date = trial.get("registration_date", "") if trial else ""
            pub_date = None
            
            if registration_date and isinstance(registration_date, str):
                try:
                    # Formato esperado: YYYY-MM-DD
                    cleaned_date = registration_date.strip()
                    if len(cleaned_date) >= 4:
                        pub_date = cleaned_date[:7]  # YYYY-MM
                except:
                    pub_date = None

            # Institución principal - normalizar
            primary_sponsor = ""
            sponsor_data = trial.get("primary_sponsor", {}) if trial else {}
            if isinstance(sponsor_data, dict):
                primary_sponsor = sponsor_data.get("name", "")
            elif isinstance(sponsor_data, str):
                primary_sponsor = sponsor_data

            if not primary_sponsor or not isinstance(primary_sponsor, str):
                primary_sponsor = ""

            # Autores/Investigadores - normalizar
            authors = []
            
            if primary_sponsor:
                authors.append(f"Sponsor: {primary_sponsor}")

            # Contacto - normalizar
            contact_name = ""
            contacts = trial.get("contacts", []) if trial else []
            
            if isinstance(contacts, list) and len(contacts) > 0:
                contact = contacts[0]
                if isinstance(contact, dict):
                    name = contact.get("name", "")
                    if name and isinstance(name, str):
                        contact_name = name.strip()
                        authors.append(f"Contact: {contact_name}")

            # Si no hay autores, poner un valor por defecto
            if not authors:
                authors = ["Investigadores no especificados"]

            # URL - normalizar
            url = f"https://trialsearch.who.int/{trial_id}" if trial_id else ""

            return NormalizedDocument(
                source_id=trial_id,
                source_type="who_ictrp",
                title=title,
                abstract=abstract,
                authors=authors,
                publication_date=pub_date,
                url=url,
                metadata={
                    "status": status,
                    "primary_sponsor": primary_sponsor,
                    "registration_date": registration_date,
                    "type": "Clinical Trial"
                }
            )
        except Exception as e:
            print(f"Error procesando ensayo WHO ICTRP: {e}")
            return None
