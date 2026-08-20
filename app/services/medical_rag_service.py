from typing import Optional

from sqlalchemy.orm import Session

from app.services.medical_search_service import MedicalSearchService
from app.services.medical_document_service import MedicalDocumentService
from app.services.medical_query_service import MedicalQueryService
from app.services.medical_response_service import MedicalResponseService
from app.services.groq_service import GroqService

from app.schemas.medical import NormalizedDocument


class MedicalRAGService:

    # ==============================================================
    # LIMITES DEL CONTEXTO PARA GROQ
    # ==============================================================

    MAX_CONTEXT_DOCUMENTS = 5
    MAX_ABSTRACT_CHARS = 2500
    MAX_TITLE_CHARS = 500
    MAX_AUTHORS = 5

    def __init__(
        self,
        db: Session,
        medical_search_service: MedicalSearchService,
        medical_document_service: MedicalDocumentService,
        medical_query_service: MedicalQueryService,
        medical_response_service: MedicalResponseService,
        groq_service: GroqService,
    ):
        self.db = db

        self.medical_search_service = medical_search_service
        self.medical_document_service = medical_document_service
        self.medical_query_service = medical_query_service
        self.medical_response_service = medical_response_service
        self.groq_service = groq_service

    # ==============================================================
    # FLUJO PRINCIPAL DEL RAG
    # ==============================================================

    async def generate_response(
        self,
        user_id: int,
        query: str,
        query_type: str = "general",
        max_results: int = 10,
        lang: str = "es",
    ) -> dict:

        medical_query = self.medical_query_service.create_query(
            user_id=user_id,
            query=query,
            query_type=query_type,
            status="processing",
        )

        try:

            # ======================================================
            # 1. BUSCAR EN PUBMED + CLINICALTRIALS + COCHRANE
            # ======================================================

            search_result = await self.medical_search_service.search(
                query=query,
                max_results=max_results,
                target_lang=lang,
            )

            documents = search_result.get(
                "results",
                [],
            )

            if not documents:
                documents = []

            # ======================================================
            # 2 & 3. PERSISTENCIA
            # ======================================================

            # Actualmente utilizamos los documentos directamente
            # en memoria para el proceso RAG.

            # ======================================================
            # 4. CONSTRUIR CONTEXTO PARA EL RAG
            # ======================================================

            context = self._build_context(
                documents
            )

            # ======================================================
            # 5. CONSTRUIR PROMPT
            # ======================================================

            prompt = self._build_prompt(
                query=query,
                context=context,
                documents=documents,
                lang=lang,
            )

            # ======================================================
            # 6. GENERAR RESPUESTA CON GROQ
            # ======================================================

            groq_result = self.groq_service.generate_response(

                prompt=prompt,

                system_prompt=(
                    "Eres un asistente médico especializado "
                    "en análisis de evidencia científica. "

                    "Tu función es analizar los documentos "
                    "científicos recuperados por el sistema "
                    "y sintetizar la información relevante "
                    "para responder la consulta del usuario. "

                    "Utiliza exclusivamente la información "
                    "contenida en los documentos proporcionados "
                    "en el contexto. "

                    "No inventes estudios, autores, resultados, "
                    "estadísticas, tratamientos ni referencias. "

                    "Cuando existan documentos recuperados, "
                    "analízalos y explica sus principales "
                    "hallazgos. "

                    "No respondas automáticamente que no existe "
                    "evidencia cuando existan documentos recuperados. "

                    "Diferencia claramente entre artículos "
                    "científicos de PubMed, estudios o ensayos "
                    "clínicos de ClinicalTrials.gov y revisiones "
                    "sistemáticas de Cochrane. "

                    "Cuando sea posible, relaciona los hallazgos "
                    "con el título real del documento que los "
                    "respalda. "

                    "Si existen resultados contradictorios, "
                    "explícalos. "

                    "Si la evidencia es realmente limitada, "
                    "indícalo y explica por qué. "

                    "Responde en el idioma solicitado por el usuario. "

                    "Responde en lenguaje comprensible. "

                    "No realices diagnósticos personalizados. "
                ),

                temperature=0.2,

                max_completion_tokens=2048,
            )

            response_text = groq_result.get(
                "response",
                "",
            )

            # ======================================================
            # FALLBACK SI GROQ DEVUELVE RESPUESTA VACÍA
            # ======================================================

            if not response_text or not response_text.strip():

                if documents:

                    response_text = (
                        f"Se encontraron {len(documents)} "
                        f"documentos científicos relacionados "
                        f"con tu consulta en PubMed, "
                        f"ClinicalTrials.gov y Cochrane. "
                        f"Puedes revisar las fuentes listadas "
                        f"a continuación para obtener más información."
                    )

                else:

                    response_text = (
                        "No se encontraron documentos científicos "
                        "relacionados en las fuentes consultadas. "
                        "Te recomiendo reformular tu consulta."
                    )

            tokens_used = groq_result.get(
                "tokens_used"
            )

            model = groq_result.get(
                "model"
            )

            # ======================================================
            # 7. GUARDAR RESPUESTA EN BASE DE DATOS
            # ======================================================

            self.medical_response_service.create_response(
                query_id=medical_query.id,
                response=response_text,
                model=model,
            )

            # ======================================================
            # 8. ACTUALIZAR ESTADO
            # ======================================================

            self.medical_query_service.update_status(
                query_id=medical_query.id,
                status="completed",
            )

            # ======================================================
            # 9. RESUMEN DE FUENTES
            # ======================================================

            source_summary = self._build_source_summary(
                documents
            )

            # ======================================================
            # 10. RESPUESTA FINAL
            # ======================================================

            return {

                "status": "success",

                "query_id": medical_query.id,

                "query": query,

                "response": response_text,

                "model": model,

                "tokens_used": tokens_used,

                "total_results": len(documents),

                "source_summary": source_summary,

                "sources": search_result.get(
                    "sources",
                    {},
                ),

                "documents": [
                    self._document_to_dict(document)
                    for document in documents
                ],
            }

        except Exception as e:

            self.medical_query_service.update_status(
                query_id=medical_query.id,
                status="error",
            )

            raise e

    # ==============================================================
    # CONTEXTO RAG
    # ==============================================================

    def _build_context(
        self,
        documents: list[NormalizedDocument],
    ) -> str:

        if not documents:

            return (
                "NO SE RECUPERARON DOCUMENTOS CIENTÍFICOS.\n\n"
                "No existen documentos disponibles en las "
                "fuentes consultadas para esta consulta."
            )

        # ==========================================================
        # LIMITAR DOCUMENTOS ENVIADOS A GROQ
        # ==========================================================

        context_documents = documents[
            :self.MAX_CONTEXT_DOCUMENTS
        ]

        context_parts = []

        for index, document in enumerate(
            context_documents,
            start=1,
        ):

            source_type = getattr(
                document,
                "source_type",
                None,
            ) or "Fuente desconocida"

            source_id = getattr(
                document,
                "source_id",
                None,
            ) or "No disponible"

            title = getattr(
                document,
                "title",
                None,
            ) or "Título no disponible"

            title = str(title)[
                :self.MAX_TITLE_CHARS
            ]

            abstract = getattr(
                document,
                "abstract",
                None,
            ) or "Resumen no disponible"

            abstract = str(abstract)[
                :self.MAX_ABSTRACT_CHARS
            ]

            # ======================================================
            # AUTORES
            # ======================================================

            authors = getattr(
                document,
                "authors",
                None,
            )

            if authors:

                if isinstance(
                    authors,
                    (list, tuple),
                ):

                    authors_list = [
                        str(author)
                        for author in authors[
                            :self.MAX_AUTHORS
                        ]
                    ]

                    authors_text = ", ".join(
                        authors_list
                    )

                else:

                    authors_text = str(
                        authors
                    )[
                        :1000
                    ]

            else:

                authors_text = "No disponible"

            publication_date = getattr(
                document,
                "publication_date",
                None,
            ) or "No disponible"

            url = getattr(
                document,
                "url",
                None,
            ) or "No disponible"

            document_type = (
                getattr(
                    document,
                    "document_type",
                    None,
                )
                or self._get_document_type(
                    source_type
                )
            )

            context_parts.append(
                f"""
==================================================
DOCUMENTO {index}
==================================================

TIPO DE EVIDENCIA:
{document_type}

FUENTE:
{source_type}

IDENTIFICADOR:
{source_id}

TÍTULO:
{title}

AUTORES:
{authors_text}

FECHA DE PUBLICACIÓN:
{publication_date}

RESUMEN:
{abstract}

URL:
{url}

==================================================
"""
            )

        context = "\n".join(
            context_parts
        )

        # ==========================================================
        # DEBUG
        # ==========================================================

        print(
            f"RAG context: "
            f"{len(context_documents)} documentos "
            f"de {len(documents)} recuperados."
        )

        print(
            f"RAG context size: "
            f"{len(context)} caracteres."
        )

        return context

    # ==============================================================
    # PROMPT PARA GROQ
    # ==============================================================

    def _build_prompt(
        self,
        query: str,
        context: str,
        documents: list[NormalizedDocument],
        lang: str = "es",
    ) -> str:

        # ==========================================================
        # SIN DOCUMENTOS
        # ==========================================================

        if not documents:

            return f"""
CONSULTA DEL USUARIO
==================================================

{query}


IDIOMA DE RESPUESTA
==================================================

{lang}


RESULTADO DE LA BÚSQUEDA
==================================================

No se recuperaron documentos científicos desde
las fuentes conectadas:

- PubMed
- ClinicalTrials.gov
- Cochrane


INSTRUCCIONES
==================================================

Indica claramente al usuario que no se encontraron
documentos científicos relacionados suficientes para
responder esta consulta.

No inventes información.

No inventes estudios.

No inventes referencias.

No intentes responder utilizando conocimiento externo
a los documentos recuperados.
"""

        # ==========================================================
        # CON DOCUMENTOS
        # ==========================================================

        context_document_count = min(
            len(documents),
            self.MAX_CONTEXT_DOCUMENTS,
        )

        return f"""
Eres un asistente médico especializado en análisis
de evidencia científica.

Tu tarea es analizar los documentos científicos
recuperados por el sistema y elaborar una respuesta
clara para el usuario.


==================================================
CONSULTA DEL USUARIO
==================================================

{query}


==================================================
IDIOMA DE RESPUESTA
==================================================

{lang}

Debes responder exclusivamente en el idioma solicitado.


==================================================
DOCUMENTOS CIENTÍFICOS RECUPERADOS
==================================================

Se recuperaron {len(documents)} documentos científicos
desde las fuentes conectadas al sistema.

Para el análisis de IA se seleccionaron
{context_document_count} documentos como contexto
principal debido a los límites de procesamiento.

Los documentos utilizados en el contexto son:

{context}


==================================================
OBJETIVO
==================================================

Utiliza los documentos anteriores para responder
la consulta del usuario.

El usuario realizó una búsqueda científica y el
sistema encontró documentos relacionados.

Por lo tanto, debes analizar esos documentos antes
de determinar si existe o no evidencia suficiente.


==================================================
ESTRUCTURA DE LA RESPUESTA
==================================================

Genera la respuesta utilizando esta estructura:


1. RESPUESTA

Explica primero y de forma clara qué indican los
documentos recuperados respecto a la consulta.

La explicación debe ser comprensible para una
persona que no necesariamente sea especialista.

No inventes información.


2. EVIDENCIA ENCONTRADA

Resume los principales hallazgos de los documentos.

Cuando sea posible, menciona el título real del
estudio o documento que respalda cada hallazgo.


3. FUENTES CONSULTADAS

Explica qué evidencia proviene de cada fuente:

- PubMed
- ClinicalTrials.gov
- Cochrane

Diferencia claramente:

- artículos científicos
- estudios observacionales
- ensayos clínicos
- registros de estudios clínicos
- revisiones sistemáticas


4. PRINCIPALES ESTUDIOS

Cuando los documentos lo permitan, identifica
los estudios más relevantes para la consulta.

Utiliza exclusivamente los títulos y datos
presentes en los documentos recuperados.


5. INTERPRETACIÓN

Explica qué puede concluirse razonablemente
a partir de la evidencia encontrada.

Si diferentes estudios presentan resultados
diferentes, indícalo.

Si existen resultados contradictorios,
explícalos.


6. LIMITACIONES

Explica las limitaciones de la evidencia
cuando sean visibles en los documentos.

Por ejemplo:

- pocos estudios
- estudios preliminares
- resultados contradictorios
- ausencia de ensayos clínicos
- evidencia indirecta
- información incompleta

No inventes limitaciones que no estén respaldadas
por los documentos.


==================================================
REGLAS CIENTÍFICAS
==================================================

1. Utiliza únicamente los documentos recuperados.

2. No utilices conocimiento externo para completar
   información que no esté presente en el contexto.

3. No inventes estudios.

4. No inventes autores.

5. No inventes resultados.

6. No inventes estadísticas.

7. No inventes tratamientos.

8. No inventes referencias.

9. No inventes conclusiones.

10. No atribuyas a un estudio información que no
    aparezca en su resumen o información recuperada.

11. Cuando menciones un estudio, utiliza su título
    real.

12. Cuando sea posible, indica la fuente.

13. Diferencia PubMed de ClinicalTrials.gov
    y Cochrane.

14. Un registro de ClinicalTrials.gov no debe
    presentarse como si fuera necesariamente
    un artículo publicado.

15. Una revisión de Cochrane debe identificarse
    como revisión sistemática.

16. Si solamente se encontraron artículos de PubMed,
    indícalo.

17. Si se encontraron ensayos clínicos, indícalos
    claramente.

18. Si se encontraron revisiones de Cochrane,
    indícalas claramente.


==================================================
REGLA MUY IMPORTANTE SOBRE LA EVIDENCIA
==================================================

NO debes responder:

"No se encontró evidencia científica suficiente"

simplemente porque los documentos no contienen
una respuesta exacta a toda la pregunta.

Si existen documentos recuperados:

1. Analiza los documentos.
2. Explica qué información relevante contienen.
3. Indica qué aspectos sí pueden responderse.
4. Indica qué aspectos no pueden determinarse.
5. Explica las limitaciones.


Solamente utiliza una respuesta de ausencia de
evidencia cuando realmente no existan documentos
relevantes o cuando los documentos recuperados
no permitan obtener ninguna información útil
para abordar la consulta.


==================================================
SEGURIDAD MÉDICA
==================================================

No realices diagnósticos personalizados.

No indiques que una persona tiene una enfermedad
basándote únicamente en la consulta.

No sustituyas la valoración de un médico.

La información debe presentarse como evidencia
científica informativa.


==================================================
OBJETIVO FINAL
==================================================

La respuesta debe ayudar al usuario a comprender:

- qué encontró la búsqueda;
- qué dicen los estudios;
- qué fuente respalda cada información;
- qué estudios son relevantes;
- qué conclusiones pueden obtenerse;
- y cuáles son las limitaciones de la evidencia.

Los documentos recuperados serán mostrados también
por el frontend como respaldo de la respuesta.

Por lo tanto, NO inventes referencias adicionales.
"""

    # ==============================================================
    # RESUMEN DE FUENTES
    # ==============================================================

    @staticmethod
    def _build_source_summary(
        documents: list[NormalizedDocument],
    ) -> dict:

        summary = {
            "pubmed": 0,
            "clinical_trials": 0,
            "cochrane": 0,
            "total": 0,
        }

        for document in documents:

            source_type = (
                getattr(
                    document,
                    "source_type",
                    None,
                )
                or ""
            ).lower().strip()

            if source_type == "pubmed":

                summary["pubmed"] += 1

            elif source_type in [
                "clinical_trials",
                "clinicaltrials",
                "clinical_trials_gov",
                "clinicaltrials.gov",
            ]:

                summary["clinical_trials"] += 1

            elif source_type == "cochrane":

                summary["cochrane"] += 1

        summary["total"] = (
            summary["pubmed"]
            + summary["clinical_trials"]
            + summary["cochrane"]
        )

        return summary

    # ==============================================================
    # TIPO DE DOCUMENTO
    # ==============================================================

    @staticmethod
    def _get_document_type(
        source_type: str,
    ) -> str:

        source = (
            source_type.lower().strip()
            if source_type
            else ""
        )

        if source == "pubmed":

            return "Artículo científico"

        if source in [
            "clinical_trials",
            "clinicaltrials",
            "clinical_trials_gov",
            "clinicaltrials.gov",
        ]:

            return "Estudio / ensayo clínico"

        if source == "cochrane":

            return "Revisión sistemática"

        return "Documento científico"

    # ==============================================================
    # SOURCE DATABASE
    # ==============================================================

    def _get_source_database_id(
        self,
        source_type: str,
    ) -> Optional[int]:

        from app.models.medical_source import MedicalSource

        if not source_type:
            return None

        source = (
            self.db.query(MedicalSource)
            .filter(
                MedicalSource.type == source_type
            )
            .first()
        )

        if not source:
            return None

        return source.id

    # ==============================================================
    # QUERY SOURCE
    # ==============================================================

    def _create_query_source(
        self,
        query_id: int,
        source_id: int,
    ):

        from app.models.medical_query_source import (
            MedicalQuerySource
        )

        existing = (
            self.db.query(MedicalQuerySource)
            .filter(
                MedicalQuerySource.query_id == query_id,
                MedicalQuerySource.source_id == source_id,
            )
            .first()
        )

        if existing:
            return existing

        query_source = MedicalQuerySource(
            query_id=query_id,
            source_id=source_id,
        )

        self.db.add(
            query_source
        )

        self.db.commit()

        self.db.refresh(
            query_source
        )

        return query_source

    # ==============================================================
    # DOCUMENT -> DICT
    # ==============================================================

    @staticmethod
    def _document_to_dict(
        document: NormalizedDocument,
    ) -> dict:

        source_type = getattr(
            document,
            "source_type",
            None,
        )

        return {
            "source_id": getattr(
                document,
                "source_id",
                None,
            ),

            "source_type": source_type,

            "document_type": (
                getattr(
                    document,
                    "document_type",
                    None,
                )
                or MedicalRAGService._get_document_type(
                    source_type or ""
                )
            ),

            "title": getattr(
                document,
                "title",
                None,
            ),

            "abstract": getattr(
                document,
                "abstract",
                None,
            ),

            "authors": getattr(
                document,
                "authors",
                [],
            ),

            "publication_date": getattr(
                document,
                "publication_date",
                None,
            ),

            "url": getattr(
                document,
                "url",
                None,
            ),

            "metadata": getattr(
                document,
                "metadata",
                {},
            ),
        }