import asyncio
import re

import argostranslate.package
import argostranslate.translate


class TranslationService:
    # ==========================================================
    # CONFIGURACIÓN
    # ==========================================================

    # Solo permitimos una traducción de Argos a la vez.
    # Esto evita que varias búsquedas simultáneas carguen
    # procesamiento de traducción al mismo tiempo.
    MAX_CONCURRENT_TRANSLATIONS = 1

    # Limitar el tamaño del texto enviado al modelo.
    # El abstract completo puede ser bastante grande.
    MAX_TEXT_CHARS = 1800

    # ==========================================================
    # PATRONES
    # ==========================================================

    # Palabras booleanas y paréntesis:
    # se preservan y no se traducen.
    BOOLEAN_SPLIT_PATTERN = re.compile(
        r"(\(|\)|\bAND\b|\bOR\b|\bNOT\b)",
        re.IGNORECASE,
    )

    # Detecta salidas degeneradas.
    REPETITION_PATTERN = re.compile(
        r"(.{2,30}?)\1{4,}"
    )

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self):
        self._ready = False

        # Evita que dos requests intenten inicializar
        # Argos al mismo tiempo.
        self._lock = asyncio.Lock()

        # Evita traducciones simultáneas.
        self._translation_semaphore = asyncio.Semaphore(
            self.MAX_CONCURRENT_TRANSLATIONS
        )

    # ==========================================================
    # ASEGURAR ARGOS LISTO
    # ==========================================================

    async def _ensure_ready(self):

        if self._ready:
            return

        async with self._lock:

            if self._ready:
                return

            print("==========================================")
            print("Inicializando Argos Translate...")
            print("==========================================")

            try:

                # IMPORTANTE:
                #
                # No descargamos modelos en cada request.
                # Primero intentamos utilizar los modelos que
                # ya estén instalados.
                await asyncio.to_thread(
                    self._check_installed_models
                )

                self._ready = True

                print(
                    "Argos Translate listo."
                )

            except Exception as e:

                print(
                    f"Error inicializando Argos Translate: {e}"
                )

                raise

    # ==========================================================
    # VERIFICAR MODELOS INSTALADOS
    # ==========================================================

    @staticmethod
    def _check_installed_models():

        required_models = {
            ("en", "es"),
            ("es", "en"),
        }

        installed_models = {
            (
                package.from_code,
                package.to_code,
            )
            for package in (
                argostranslate.package.get_installed_packages()
            )
        }

        missing_models = (
            required_models - installed_models
        )

        if missing_models:

            print(
                "ADVERTENCIA: Faltan modelos de Argos:"
            )

            for source, target in missing_models:

                print(
                    f" - {source} -> {target}"
                )

            print(
                "La aplicación intentará utilizar "
                "los modelos disponibles."
            )

    # ==========================================================
    # INSTALAR MODELOS
    # ==========================================================

    @staticmethod
    def _install_models():

        print(
            "Instalando modelos de Argos Translate..."
        )

        argostranslate.package.update_package_index()

        available = (
            argostranslate.package
            .get_available_packages()
        )

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

        for from_code, to_code in [
            ("en", "es"),
            ("es", "en"),
        ]:

            if (
                from_code,
                to_code,
            ) in installed:

                print(
                    f"Modelo {from_code} -> {to_code} "
                    f"ya instalado."
                )

                continue

            package = next(
                (
                    package
                    for package in available
                    if (
                        package.from_code == from_code
                        and
                        package.to_code == to_code
                    )
                ),
                None,
            )

            if not package:

                print(
                    f"No se encontró modelo "
                    f"{from_code} -> {to_code}"
                )

                continue

            print(
                f"Descargando modelo "
                f"{from_code} -> {to_code}..."
            )

            downloaded_path = (
                package.download()
            )

            argostranslate.package.install_from_path(
                downloaded_path
            )

            print(
                f"Modelo {from_code} -> {to_code} "
                f"instalado correctamente."
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
        # LIMITAR TEXTO
        # ------------------------------------------------------

        original_text = text

        if len(text) > self.MAX_TEXT_CHARS:

            text = text[:self.MAX_TEXT_CHARS]

            print(
                f"Texto limitado para traducción: "
                f"{len(original_text)} -> "
                f"{len(text)} caracteres"
            )

        # ------------------------------------------------------
        # ASEGURAR MODELO
        # ------------------------------------------------------

        try:

            await self._ensure_ready()

        except Exception as e:

            print(
                f"No fue posible inicializar Argos: {e}"
            )

            return original_text

        # ------------------------------------------------------
        # CONTROL DE CONCURRENCIA
        # ------------------------------------------------------

        async with self._translation_semaphore:

            try:

                print(
                    f"Traduciendo "
                    f"{source} -> {target} "
                    f"({len(text)} caracteres)"
                )

                translated = await asyncio.to_thread(
                    argostranslate.translate.translate,
                    text,
                    source,
                    target,
                )

                if not translated:

                    return original_text

                # --------------------------------------------------
                # VALIDAR RESULTADO
                # --------------------------------------------------

                if self._looks_degenerate(
                    translated
                ):

                    print(
                        "Traducción degenerada detectada. "
                        "Se conserva el texto original."
                    )

                    return original_text

                return translated

            except Exception as e:

                print(
                    f"Argos Translate error: {e}"
                )

                return original_text

    # ==========================================================
    # TRADUCIR CONSULTA BOOLEANA
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

        # ------------------------------------------------------
        # LIMITAR CONSULTA
        # ------------------------------------------------------

        if len(text) > self.MAX_TEXT_CHARS:

            text = text[
                :self.MAX_TEXT_CHARS
            ]

        # ------------------------------------------------------
        # SEPARAR BOOLEANOS
        # ------------------------------------------------------

        parts = self.BOOLEAN_SPLIT_PATTERN.split(
            text
        )

        translated_parts = []

        for part in parts:

            stripped = part.strip()

            if not stripped:

                translated_parts.append(part)

                continue

            # Preservar operadores y paréntesis.
            if stripped.upper() in (
                "(",
                ")",
                "AND",
                "OR",
                "NOT",
            ):

                translated_parts.append(
                    part
                )

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