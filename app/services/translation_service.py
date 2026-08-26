import asyncio
import re

import argostranslate.package
import argostranslate.translate


class TranslationService:

    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    MAX_CONCURRENT_TRANSLATIONS = 1

    # Para evitar enviar textos enormes al modelo.
    MAX_TEXT_CHARS = 1800

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
                "INICIALIZANDO ARGOS TRANSLATE"
            )
            print(
                "=========================================="
            )

            try:

                await asyncio.to_thread(
                    self._install_missing_models
                )

                self._ready = True

                print(
                    "Argos Translate listo."
                )

            except Exception as e:

                print(
                    f"Error preparando Argos Translate: {e}"
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
        # ASEGURAR MODELOS
        # ------------------------------------------------------

        try:

            await self._ensure_ready()

        except Exception as e:

            print(
                f"No fue posible preparar Argos: {e}"
            )

            return text

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
                        "Argos devolvió una traducción vacía."
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
                    f"Argos Translate error: {e}"
                )

                return text

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

        return (
            len(text) > 300
            and bool(
                TranslationService
                .REPETITION_PATTERN
                .search(text)
            )
        )