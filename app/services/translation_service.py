import asyncio
import re

import argostranslate.package
import argostranslate.translate


class TranslationService:

    # Palabras booleanas y paréntesis: se preservan, no se traducen
    BOOLEAN_SPLIT_PATTERN = re.compile(r'(\(|\)|\bAND\b|\bOR\b|\bNOT\b)')

    # Detecta salidas "degeneradas": un fragmento que se repite muchas veces
    # seguidas (típico fallo de modelos chicos ante texto sin sentido)
    REPETITION_PATTERN = re.compile(r'(.{2,30}?)\1{4,}')

    def __init__(self):
        self._ready = False
        self._lock = asyncio.Lock()

    # ==========================================================
    # DESCARGAR/INSTALAR MODELOS (una sola vez)
    # ==========================================================

    async def _ensure_ready(self):

        if self._ready:
            return

        async with self._lock:

            if self._ready:
                return

            await asyncio.to_thread(self._install_models)
            self._ready = True

    @staticmethod
    def _install_models():

        argostranslate.package.update_package_index()

        available = argostranslate.package.get_available_packages()

        installed = {
            (p.from_code, p.to_code)
            for p in argostranslate.package.get_installed_packages()
        }

        for from_code, to_code in [("en", "es"), ("es", "en")]:

            if (from_code, to_code) in installed:
                continue

            package = next(
                (p for p in available
                 if p.from_code == from_code and p.to_code == to_code),
                None,
            )

            if package:
                print(f"Descargando modelo {from_code} -> {to_code}...")
                argostranslate.package.install_from_path(package.download())

    # ==========================================================
    # TRADUCIR TEXTO NATURAL (títulos, abstracts, etc.)
    # ==========================================================

    async def translate(
        self,
        text: str,
        source: str = "en",
        target: str = "es",
    ) -> str:

        if not text:
            return text

        if source == target:
            return text

        await self._ensure_ready()

        try:
            translated = await asyncio.to_thread(
                argostranslate.translate.translate, text, source, target
            )

            if self._looks_degenerate(translated):
                print(f"Traducción degenerada detectada, se descarta: {translated[:80]}...")
                return text

            return translated

        except Exception as e:
            print(f"Argos Translate error: {e}")
            return text

    # ==========================================================
    # TRADUCIR CONSULTA BOOLEANA (AND/OR/NOT, paréntesis)
    # ==========================================================

    async def translate_query(
        self,
        text: str,
        source: str = "es",
        target: str = "en",
    ) -> str:

        if not text:
            return text

        if source == target:
            return text

        parts = self.BOOLEAN_SPLIT_PATTERN.split(text)
        translated_parts = []

        for part in parts:

            stripped = part.strip()

            if not stripped or stripped in ("(", ")", "AND", "OR", "NOT"):
                translated_parts.append(part)
                continue

            translated_term = await self.translate(stripped, source, target)
            translated_parts.append(translated_term)

        return "".join(translated_parts)

    # ==========================================================
    # DETECTAR TRADUCCIÓN DEGENERADA
    # ==========================================================

    @staticmethod
    def _looks_degenerate(text: str) -> bool:
        return len(text) > 300 and bool(
            TranslationService.REPETITION_PATTERN.search(text)
        )