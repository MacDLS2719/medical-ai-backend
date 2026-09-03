from babel import Locale


SUPPORTED_LANGUAGES = {
    "es": "Español",
    "en": "English",
}

DEFAULT_LANGUAGE = "es"


def normalize_language(language: str | None) -> str:
    """
    Convierte códigos como:
    es-CO -> es
    es-MX -> es
    en-US -> en
    en-GB -> en
    """

    if not language:
        return DEFAULT_LANGUAGE

    language = language.lower().replace("_", "-")

    language_code = language.split("-")[0]

    if language_code in SUPPORTED_LANGUAGES:
        return language_code

    return DEFAULT_LANGUAGE


def get_locale(language: str | None) -> Locale:
    language_code = normalize_language(language)

    return Locale.parse(language_code)
