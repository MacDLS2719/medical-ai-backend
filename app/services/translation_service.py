import asyncio
import re
from typing import Optional

from deep_translator import GoogleTranslator, DeeplTranslator
from app.core.config import settings

import argostranslate.package
import argostranslate.translate


class TranslationService:

    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    MAX_CONCURRENT_TRANSLATIONS = 3

    # Para evitar enviar textos enormes al modelo.
    MAX_TEXT_CHARS = 1800

    # Límite de caracteres para servicios gratuitos
    MAX_CHARS_PER_REQUEST = 5000

    # ==========================================================
    # PATRONES
    # ==========================================================

    BOOLEAN_SPLIT_PATTERN = re.compile(
        r"(\(|\)|\bAND\b|\bOR\b|\bNOT\b)",
        re.IGNORECASE,
    )

    REPETITION_PATTERN = re.compile(
        r"(.{2,30}?)\1{4,}"
    )

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self):

        self._ready = False

        # Evita inicializaciones simultáneas.
        self._lock = asyncio.Lock()

        # Solo una traducción a la vez.
        self._translation_semaphore = asyncio.Semaphore(
            self.MAX_CONCURRENT_TRANSLATIONS
        )

        # Determinar qué servicio usar
        self.translation_service = settings.TRANSLATION_SERVICE.lower()
        self.use_local = settings.USE_LOCAL_TRANSLATION

        # Inicializar traductores
        self._deepl_translator = None
        self._google_translator = None

        if self.translation_service == "deepl" and settings.DEEPL_API_KEY:
            try:
                self._deepl_translator = DeeplTranslator(
                    api_key=settings.DEEPL_API_KEY,
                    source="auto",
                    target="es"
                )
                print("DeepL translator initialized")
            except Exception as e:
                print(f"Failed to initialize DeepL: {e}")
                self.translation_service = "google"

        # Siempre inicializar Google Translate (con o sin API key)
        try:
            if settings.GOOGLE_TRANSLATE_API_KEY:
                self._google_translator = GoogleTranslator(
                    source="auto",
                    target="es",
                    api_key=settings.GOOGLE_TRANSLATE_API_KEY
                )
                print("Google translator initialized with API key")
            else:
                self._google_translator = GoogleTranslator(source="auto", target="es")
                print("Google translator initialized (free version)")
        except Exception as e:
            print(f"Failed to initialize Google Translate: {e}")
            # Intentar versión gratuita
            try:
                self._google_translator = GoogleTranslator(source="auto", target="es")
                print("Google translator initialized (free version fallback)")
            except Exception as e2:
                print(f"Failed to initialize Google Translate free version: {e2}")

    # ==========================================================
    # ASEGURAR MODELOS
    # ==========================================================

    async def _ensure_ready(self):

        if self._ready:
            return

        async with self._lock:

            if self._ready:
                return

            print(
                "=========================================="
            )
            print(
                f"INICIALIZANDO SERVICIO DE TRADUCCIÓN: {self.translation_service}"
            )
            print(
                "=========================================="
            )

            try:
                # Solo inicializar argos si está configurado para local
                if self.use_local:
                    await asyncio.to_thread(
                        self._install_missing_models
                    )
                    print("Argos Translate listo para uso local.")
                else:
                    print("Usando servicio de traducción en la nube.")

                self._ready = True

            except Exception as e:

                print(
                    f"Error preparando servicio de traducción: {e}"
                )

                raise

    # ==========================================================
    # INSTALAR MODELOS FALTANTES
    # ==========================================================

    @staticmethod
    def _install_missing_models():

        required_models = [
            ("en", "es"),
            ("es", "en"),
        ]

        # ------------------------------------------------------
        # MODELOS INSTALADOS
        # ------------------------------------------------------

        installed = {
            (
                package.from_code,
                package.to_code,
            )
            for package in (
                argostranslate.package
                .get_installed_packages()
            )
        }

        print(
            f"Modelos Argos instalados: {installed}"
        )

        missing_models = [
            (
                source,
                target
            )
            for source, target in required_models
            if (
                source,
                target
            ) not in installed
        ]

        # ------------------------------------------------------
        # TODO INSTALADO
        # ------------------------------------------------------

        if not missing_models:

            print(
                "Los modelos EN<->ES ya están instalados."
            )

            return

        print(
            "Modelos faltantes:"
        )

        for source, target in missing_models:

            print(
                f" - {source} -> {target}"
            )

        # ------------------------------------------------------
        # ACTUALIZAR ÍNDICE
        # ------------------------------------------------------

        print(
            "Actualizando índice de paquetes Argos..."
        )

        argostranslate.package.update_package_index()

        available = (
            argostranslate.package
            .get_available_packages()
        )

        # ------------------------------------------------------
        # INSTALAR
        # ------------------------------------------------------

        for source, target in missing_models:

            print(
                f"Buscando modelo "
                f"{source} -> {target}..."
            )

            package = next(
                (
                    package
                    for package in available
                    if (
                        package.from_code == source
                        and
                        package.to_code == target
                    )
                ),
                None,
            )

            if not package:

                raise RuntimeError(
                    f"No se encontró el modelo "
                    f"{source} -> {target}"
                )

            print(
                f"Descargando modelo "
                f"{source} -> {target}..."
            )

            package_path = package.download()

            print(
                f"Instalando modelo "
                f"{source} -> {target}..."
            )

            argostranslate.package.install_from_path(
                package_path
            )

            print(
                f"Modelo "
                f"{source} -> {target} "
                f"instalado correctamente."
            )

        print(
            "Todos los modelos requeridos "
            "están disponibles."
        )

    # ==========================================================
    # TRADUCIR TEXTO
    # ==========================================================

    async def translate(
        self,
        text: str,
        source: str = "en",
        target: str = "es",
    ) -> str:

        if not text:
            return text

        source = source.strip().lower()
        target = target.strip().lower()

        if source == target:
            return text

        # ------------------------------------------------------
        # ASEGURAR MODELOS (solo para local)
        # ------------------------------------------------------

        if self.use_local:
            try:
                await self._ensure_ready()
            except Exception as e:
                print(f"No fue posible preparar Argos: {e}")
                # Fallback a servicios en la nube
                self.use_local = False

        # ------------------------------------------------------
        # LIMITAR TEXTO
        # ------------------------------------------------------

        text_to_translate = text

        if len(text_to_translate) > self.MAX_TEXT_CHARS:

            text_to_translate = (
                text_to_translate[
                    :self.MAX_TEXT_CHARS
                ]
            )

            print(
                f"Texto limitado: "
                f"{len(text)} -> "
                f"{len(text_to_translate)} caracteres"
            )

        # ------------------------------------------------------
        # TRADUCCIÓN CONTROLADA
        # ------------------------------------------------------

        async with self._translation_semaphore:

            try:

                print(
                    "------------------------------------------"
                )

                print(
                    f"TRADUCCIÓN: "
                    f"{source} -> {target}"
                )

                print(
                    f"CARACTERES: "
                    f"{len(text_to_translate)}"
                )

                # --------------------------------------------------
                # USAR SERVICIO EN LA NUBE (prioridad)
                # --------------------------------------------------

                if not self.use_local:
                    translated = await self._translate_with_cloud(
                        text_to_translate,
                        source,
                        target
                    )
                else:
                    # Fallback a argos local
                    translated = await asyncio.to_thread(
                        argostranslate.translate.translate,
                        text_to_translate,
                        source,
                        target,
                    )

                # --------------------------------------------------
                # VALIDAR
                # --------------------------------------------------

                if not translated:

                    print(
                        "Servicio devolvió una traducción vacía."
                    )

                    return text

                if self._looks_degenerate(
                    translated
                ):

                    print(
                        "Traducción degenerada detectada."
                    )

                    return text

                print(
                    "Traducción completada."
                )

                return translated

            except Exception as e:

                print(
                    f"Error en traducción: {e}"
                )

                # Intentar fallback si falla el servicio principal
                if not self.use_local:
                    print("Intentando fallback a servicio alternativo...")
                    try:
                        translated = await self._translate_with_fallback(
                            text_to_translate,
                            source,
                            target
                        )
                        if translated and not self._looks_degenerate(translated):
                            return translated
                    except Exception as fallback_error:
                        print(f"Fallback también falló: {fallback_error}")

                return text

    # ==========================================================
    # TRADUCIR CON SERVICIO EN LA NUBE
    # ==========================================================

    async def _translate_with_cloud(
        self,
        text: str,
        source: str,
        target: str
    ) -> str:

        try:
            # Prioridad: DeepL -> Google
            if self.translation_service == "deepl" and self._deepl_translator:
                print("Usando DeepL para traducción")
                return await asyncio.to_thread(
                    self._deepl_translator.translate,
                    text,
                    source=source,
                    target=target
                )
            elif self._google_translator:
                print("Usando Google Translate para traducción")
                return await asyncio.to_thread(
                    self._google_translator.translate,
                    text,
                    source=source,
                    target=target
                )
            else:
                # Fallback a Google Translate gratuito
                print("Creando Google Translator temporal como fallback")
                translator = GoogleTranslator(source=source, target=target)
                return await asyncio.to_thread(
                    translator.translate,
                    text
                )

        except Exception as e:
            print(f"Error con servicio {self.translation_service}: {e}")
            raise

    # ==========================================================
    # TRADUCIR CON FALLBACK
    # ==========================================================

    async def _translate_with_fallback(
        self,
        text: str,
        source: str,
        target: str
    ) -> str:

        try:
            # Si falló DeepL, intentar Google
            if self.translation_service == "deepl":
                print("Intentando Google Translate como fallback...")
                translator = GoogleTranslator(source=source, target=target)
                return await asyncio.to_thread(
                    translator.translate,
                    text
                )
            # Si falló Google, intentar DeepL
            elif self.translation_service == "google":
                if self._deepl_translator:
                    print("Intentando DeepL como fallback...")
                    return await asyncio.to_thread(
                        self._deepl_translator.translate,
                        text,
                        source=source,
                        target=target
                    )
                else:
                    # Crear translator temporal
                    print("Intentando DeepL temporal como fallback...")
                    temp_translator = DeeplTranslator(
                        api_key=settings.DEEPL_API_KEY,
                        source=source,
                        target=target
                    )
                    return await asyncio.to_thread(
                        temp_translator.translate,
                        text
                    )

        except Exception as e:
            print(f"Error en fallback: {e}")
            raise

    # ==========================================================
    # TRADUCIR CONSULTA BOOLEAN
    # ==========================================================

    async def translate_query(
        self,
        text: str,
        source: str = "es",
        target: str = "en",
    ) -> str:

        if not text:
            return text

        source = source.strip().lower()
        target = target.strip().lower()

        if source == target:
            return text

        parts = self.BOOLEAN_SPLIT_PATTERN.split(
            text
        )

        translated_parts = []

        for part in parts:

            stripped = part.strip()

            if not stripped:

                translated_parts.append(part)

                continue

            upper = stripped.upper()

            if upper in (
                "(",
                ")",
                "AND",
                "OR",
                "NOT",
            ):

                translated_parts.append(part)

                continue

            translated_term = await self.translate(
                stripped,
                source,
                target,
            )

            translated_parts.append(
                translated_term
            )

        return "".join(
            translated_parts
        )

    # ==========================================================
    # DETECTAR TRADUCCIÓN DEGENERADA
    # ==========================================================

    @staticmethod
    def _looks_degenerate(
        text: str
    ) -> bool:

        if not text:
            return False

        # Detectar repeticiones excesivas (signo de traducción fallida)
        return (
            len(text) > 300
            and bool(
                TranslationService
                .REPETITION_PATTERN
                .search(text)
            )
        )