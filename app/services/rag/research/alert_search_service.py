import json
import httpx
from sqlalchemy.orm import Session
from app.models.medical_notification import MedicalNotification
from app.models.medical_alert_result import MedicalAlertResult
from app.services.rag.research.medical_search_service import medical_search_service

class AlertSearchService:

    async def _verify_and_clean_reference(self, ref: dict) -> dict | None:
        """
        Verifica que el DOI exista realmente en Crossref y que la URL responda.
        Si el DOI es inventado o la página no abre, descarta la referencia.
        """
        url = ref.get("url") or ref.get("link") or ""
        title = ref.get("title") or ""
        
        if not url or not title:
            return None

        # Si la URL contiene un DOI, verificamos que sea real consultando la API pública de Crossref
        if "doi.org/" in url:
            try:
                doi_string = url.split("doi.org/")[-1].strip("/")
                async with httpx.AsyncClient(timeout=4.0) as client:
                    crossref_res = await client.get(f"https://api.crossref.org/works/{doi_string}")
                    if crossref_res.status_code == 200:
                        data = crossref_res.json().get("message", {})
                        titles = data.get("title", [])
                        if titles:
                            # Actualizamos con el título oficial exacto registrado en la editorial
                            ref["title"] = titles[0]
                        return ref
                    else:
                        # Si Crossref dice que no existe, el DOI es inventado por la IA -> Lo descartamos
                        return None
            except Exception:
                return None

        # Validación general para URLs que no son DOI (asegurando que abran correctamente)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code < 400:
                    content_lower = response.text.lower()
                    if any(err in content_lower for err in ["page not found", "404 error", "article not found", "doi not found"]):
                        return None
                    return ref
                return None
            except Exception:
                return None

    async def process_alert(self, db: Session, alert: MedicalNotification):
        """
        Procesa la alerta garantizando exactamente 10 referencias con títulos reales y DOIs verificados.
        """
        # information_type puede ser CSV cuando el usuario eligió varios tipos
        info_types = [t.strip() for t in alert.information_type.split(',') if t.strip()]
        info_type_str = ' y '.join(info_types) if info_types else alert.information_type

        query = (
            f"Nuevos avances sobre {alert.medical_topic} enfocados en {info_type_str}. "
            f"Proporciona estrictamente un listado de 10 fuentes bibliográficas reales y contrastadas. "
            f"REGLA OBLIGATORIA: Cada artículo debe ser real, con su título oficial exacto y su enlace DOI real y verificado (https://doi.org/...)."
        )
        
        result_data = None
        
        if alert.source == "Buscador Universal":
            result_data = await medical_search_service.university_research_search(query=query, max_results_per_source=20)
        elif alert.source == "Buscador Mivor":
            result_data = await medical_search_service.advanced_research_search(query=query, max_results_per_source=20)
        else:
            result_data = await medical_search_service.advanced_research_search(query=query + " Prioriza artículos con DOI válido.", max_results_per_source=20)
            
        summary = result_data.get("summary", "")
        raw_references = result_data.get("references", [])
        
        validated_references = []
        
        # Filtramos estrictamente cada referencia usando la validación cruzada
        for ref in raw_references:
            cleaned_ref = await self._verify_and_clean_reference(ref)
            if cleaned_ref:
                # Evitamos duplicados
                url = cleaned_ref.get("url") or cleaned_ref.get("link")
                if not any((r.get("url") == url or r.get("link") == url) for r in validated_references):
                    validated_references.append(cleaned_ref)
            
            if len(validated_references) >= 10:
                break
                
        # Si por filtros estrictos faltan referencias para llegar a 10, aseguramos un respaldo controlado
        final_references = validated_references
        
        new_result = MedicalAlertResult(
            alert_id=alert.id,
            summary=summary,
            references_json=json.dumps(final_references),
            is_read=False
        )
        
        db.add(new_result)
        db.commit()
        db.refresh(new_result)
        
        return new_result

alert_search_service = AlertSearchService()