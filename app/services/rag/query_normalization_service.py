import re
from typing import Literal

from langdetect import detect, LangDetectException


QueryType = Literal["disease", "medication", "both", "unknown"]


class QueryNormalizationService:
    """
    Servicio encargado de normalizar y analizar las consultas médicas.

    Responsabilidades:
    - Detectar el idioma de la consulta.
    - Limpiar la consulta.
    - Eliminar palabras de intención que no aportan al motor de búsqueda.
    - Clasificar la consulta como enfermedad, medicamento, ambos o desconocida.

    Este servicio NO decide qué fuentes consultar.
    Esa responsabilidad pertenece a MedicalSearchOrchestrator.
    """

    # Palabras que expresan intención pero que normalmente no aportan
    # información relevante para las búsquedas en las fuentes médicas.
    INTENT_STOPWORDS = {
        # Español
        "buscar",
        "busca",
        "buscame",
        "encuentra",
        "encontrar",
        "información",
        "informacion",
        "artículos",
        "articulos",
        "estudios",
        "investigaciones",
        "evidencia",
        "evidencias",
        "quiero",
        "necesito",
        "dame",
        "muéstrame",
        "muestrame",
        "mostrar",
        "sobre",
        "acerca",
        "relacionado",
        "relacionados",
        "últimos",
        "ultimos",
        "recientes",
        "avances",
        "avance",
        "novedades",
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "para",
        "con",
        "por",
        "qué",
        "que",
        "como",
        "cómo",

        # Inglés
        "search",
        "find",
        "looking",
        "information",
        "articles",
        "studies",
        "research",
        "evidence",
        "show",
        "give",
        "about",
        "related",
        "latest",
        "recent",
    }

    # Términos que permiten identificar una consulta relacionada
    # con medicamentos.
    MEDICATION_KEYWORDS = {
        # Español
        "medicamento",
        "medicamentos",
        "fármaco",
        "farmaco",
        "fármacos",
        "farmacos",
        "droga",
        "drogas",
        "tratamiento farmacológico",
        "tratamiento farmacologico",
        "dosis",
        "dosificación",
        "dosificacion",
        "efectos adversos",
        "efecto adverso",
        "interacción",
        "interacciones",

        # Inglés
        "drug",
        "drugs",
        "medication",
        "medications",
        "medicine",
        "medicines",
        "pharmacological treatment",
        "dose",
        "dosage",
        "adverse effect",
        "adverse effects",
        "side effect",
        "side effects",
        "interaction",
        "interactions",
    }

    # Términos que permiten identificar una consulta relacionada
    # con enfermedades o patologías.
    DISEASE_KEYWORDS = {
        # Español
        "enfermedad",
        "enfermedades",
        "patología",
        "patologia",
        "patologías",
        "patologias",
        "síndrome",
        "sindrome",
        "síndromes",
        "sindromes",
        "trastorno",
        "trastornos",
        "cáncer",
        "cancer",
        "infección",
        "infeccion",
        "infecciones",

        # Inglés
        "disease",
        "diseases",
        "pathology",
        "pathologies",
        "syndrome",
        "syndromes",
        "disorder",
        "disorders",
        "cancer",
        "infection",
        "infections",
    }

    def normalize(self, query: str) -> dict:
        """
        Normaliza y analiza una consulta médica.

        Retorna:
        {
            "original_query": str,
            "normalized_query": str,
            "language": str,
            "query_type": str
        }
        """

        if not query or not query.strip():
            return {
                "original_query": query or "",
                "normalized_query": "",
                "language": "unknown",
                "query_type": "unknown",
            }

        original_query = query.strip()

        language = self.detect_language(original_query)

        normalized_query = self.clean_query(original_query)

        query_type = self.classify_query(normalized_query)

        return {
            "original_query": original_query,
            "normalized_query": normalized_query,
            "language": language,
            "query_type": query_type,
        }

    def detect_language(self, query: str) -> str:
        """
        Detecta el idioma utilizando langdetect.

        Si no puede determinar el idioma, retorna 'unknown'.
        """

        try:
            language = detect(query)

            # Normalizamos los códigos que nos interesan.
            if language.startswith("es"):
                return "es"

            if language.startswith("en"):
                return "en"

            return language

        except LangDetectException:
            return "unknown"

        except Exception:
            return "unknown"

    def clean_query(self, query: str) -> str:
        """
        Limpia la consulta eliminando palabras de intención
        innecesarias para la búsqueda médica.
        """

        # Normalizar espacios.
        query = re.sub(r"\s+", " ", query).strip()

        # Normalizar caracteres innecesarios, conservando letras,
        # números, espacios y caracteres médicos comunes.
        query = re.sub(
            r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ\-\/\.]",
            " ",
            query,
        )

        words = query.split()

        cleaned_words = []

        for word in words:
            normalized_word = word.lower().strip()

            if normalized_word in self.INTENT_STOPWORDS:
                continue

            cleaned_words.append(word)

        normalized_query = " ".join(cleaned_words)

        # Evitar espacios duplicados.
        normalized_query = re.sub(
            r"\s+",
            " ",
            normalized_query,
        ).strip()

        # Quitar puntuación suelta al final (ej: "cáncer." → "cáncer")
        normalized_query = normalized_query.rstrip(".,;:!?")

        return normalized_query

    def classify_query(self, query: str) -> QueryType:
        """
        Clasifica la consulta como:

        - disease
        - medication
        - both
        - unknown

        La clasificación no determina las fuentes.
        """

        normalized_query = query.lower()

        medication_found = self._contains_keyword(
            normalized_query,
            self.MEDICATION_KEYWORDS,
        )

        disease_found = self._contains_keyword(
            normalized_query,
            self.DISEASE_KEYWORDS,
        )

        if medication_found and disease_found:
            return "both"

        if medication_found:
            return "medication"

        if disease_found:
            return "disease"

        return "unknown"

    @staticmethod
    def _contains_keyword(
        query: str,
        keywords: set[str],
    ) -> bool:
        """
        Determina si alguno de los términos médicos está presente
        en la consulta.
        """

        for keyword in keywords:
            if " " in keyword:
                if keyword in query:
                    return True
            else:
                pattern = rf"\b{re.escape(keyword)}\b"

                if re.search(pattern, query):
                    return True

        return False