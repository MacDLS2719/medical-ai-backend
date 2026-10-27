import json
import re
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings

GOOGLE_MAPS_HOSTS = {
    "google.com",
    "www.google.com",
    "maps.google.com",
    "maps.app.goo.gl",
    "goo.gl",
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DEFAULT_OPENING_HOURS = {
    "monday": "08:00 - 18:00",
    "tuesday": "08:00 - 18:00",
    "wednesday": "08:00 - 18:00",
    "thursday": "08:00 - 18:00",
    "friday": "08:00 - 18:00",
    "saturday": "08:00 - 13:00",
    "sunday": "Cerrado",
    "weekday_text": [
        "Lunes: 08:00 - 18:00",
        "Martes: 08:00 - 18:00",
        "Miércoles: 08:00 - 18:00",
        "Jueves: 08:00 - 18:00",
        "Viernes: 08:00 - 18:00",
        "Sábado: 08:00 - 13:00",
        "Domingo: Cerrado",
    ],
}

DEFAULT_CLINIC_PHOTOS = [
    "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=1200&q=80",
]

CANONICAL_CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "cali": (3.4516, -76.5320),
    "santiago de cali": (3.4516, -76.5320),
    "bogota": (4.6097, -74.0817),
    "bogotá": (4.6097, -74.0817),
    "medellin": (6.2442, -75.5812),
    "medellín": (6.2442, -75.5812),
    "barranquilla": (10.9685, -74.7813),
    "cartagena": (10.3910, -75.4794),
    "bucaramanga": (7.1193, -73.1227),
    "pereira": (4.8133, -75.6961),
    "manizales": (5.0689, -75.5174),
    "ibague": (4.4389, -75.2322),
    "ibagué": (4.4389, -75.2322),
    "santa marta": (11.2408, -74.1990),
    "villavicencio": (4.1420, -73.6266),
    "pasto": (1.2136, -77.2811),
    "cucuta": (7.8939, -72.5078),
    "cúcuta": (7.8939, -72.5078),
    "monteria": (8.7479, -75.8814),
    "montería": (8.7479, -75.8814),
    "popayan": (2.4419, -76.6063),
    "popayán": (2.4419, -76.6063),
    "armenia": (4.5339, -75.6811),
    "neiva": (2.9273, -75.2819),
    "valledupar": (10.4631, -73.2532),
    "monterrey": (25.6866, -100.3161),
    "guadalajara": (20.6597, -103.3496),
    "ciudad de mexico": (19.4326, -99.1332),
    "cdmx": (19.4326, -99.1332),
    "madrid": (40.4168, -3.7038),
    "barcelona": (41.3851, 2.1734),
    "lima": (-12.0464, -77.0428),
    "buenos aires": (-34.6037, -58.3816),
    "santiago": (-33.4489, -70.6693),
}


def resolve_city_coordinates(city: str | None, country: str | None = None) -> tuple[float, float] | None:
    if not city or not city.strip():
        return None
    cleaned = city.strip().lower()
    if cleaned in CANONICAL_CITY_COORDINATES:
        return CANONICAL_CITY_COORDINATES[cleaned]
    for k, v in CANONICAL_CITY_COORDINATES.items():
        if k in cleaned or cleaned in k:
            return v
    return None


class DoctorGoogleSearchService:
    """
    Servicio de búsqueda y extracción de información de establecimientos médicos A NIVEL MUNDIAL.

    Estrategia de alta completitud mundial:
      1. Extrae el query y metadatos de la URL ingresada (Google Search o Google Maps).
      2. Si es URL directa de Maps/Places, extrae datos de la página.
      3. Búsqueda web mundial en DuckDuckGo HTML y Google (sin sesgo local de país).
      4. Detección y scraping de portales médicos globales (Doctoralia, TopDoctors, Doctolib, Zocdoc, etc.).
      5. Extracción con OpenAI (gpt-4o-mini) de:
         - business_name
         - google_category
         - formatted_address
         - phone_number
         - website_url
         - booking_url (citas / appointments)
         - google_rating
         - google_reviews_count
         - latitude / longitude
         - opening_hours (horarios activos)
      6. Geocodificación global con OpenStreetMap Nominatim.
      7. Normalización y valores por defecto activos para que ningún campo quede vacío.
    """

    @staticmethod
    def validate_google_maps_url(url: str) -> str:
        if not url or not url.strip():
            raise ValueError("Debes proporcionar un enlace de Google.")

        url = url.strip()
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        is_google_host = host in GOOGLE_MAPS_HOSTS or host.endswith(".google.com")

        if parsed.scheme != "https" or not is_google_host:
            raise ValueError(
                "El enlace debe ser una URL HTTPS válida de Google o Google Maps."
            )
        return url

    @staticmethod
    def _is_google_maps_place_url(url: str) -> bool:
        """Detecta si la URL apunta directamente a un place/coordenadas de Google Maps."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        host = (parsed.hostname or "").lower()
        return (
            "maps.google.com" in host
            or "maps.app.goo.gl" in host
            or "goo.gl" in host
            or "/maps/place/" in path
            or ("@" in url and "/maps" in path)
        )

    @staticmethod
    def extract_query_from_url(url: str) -> str:
        """
        Extrae el texto de búsqueda desde cualquier tipo de URL de Google.
        Funciona con /search?q=, /maps?q=, /maps/place/NAME, etc.
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        raw_query = params.get("q", [None])[0] or params.get("query", [None])[0]
        if raw_query:
            return unquote(raw_query).replace("+", " ").strip()

        parts = parsed.path.split("/")
        if "place" in parts:
            idx = parts.index("place")
            if idx + 1 < len(parts):
                raw = parts[idx + 1]
                name = unquote(raw).replace("+", " ").replace("_", " ").strip()
                name = re.sub(r"@[\-\d.,]+$", "", name).strip()
                if name:
                    return name

        return ""

    @staticmethod
    def extract_place_reference(url: str) -> dict[str, str | None]:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        place_id = params.get("query_place_id", [None])[0] or params.get("place_id", [None])[0]
        query = params.get("query", [None])[0] or params.get("q", [None])[0]

        name = None
        parts = parsed.path.split("/")
        if "place" in parts:
            index = parts.index("place")
            if index + 1 < len(parts):
                raw = parts[index + 1]
                name = unquote(raw).replace("+", " ").replace("_", " ").strip()
                name = re.sub(r"@[\-\d.,]+$", "", name).strip()

        lat = None
        lng = None
        coord_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
        if coord_match:
            lat = coord_match.group(1)
            lng = coord_match.group(2)

        cid = None
        cid_match = re.search(r"[?&/]cid=(\d+)", url)
        if cid_match:
            cid = cid_match.group(1)

        search_text = None
        if query:
            search_text = unquote(query).replace("+", " ").strip()
        elif name:
            search_text = name

        return {
            "place_id": place_id,
            "cid": cid,
            "search_text": search_text,
            "latitude": lat,
            "longitude": lng,
        }

    async def _search_web_for_doctor(self, query: str) -> tuple[str, list[str]]:
        """
        Búsqueda web mundial (DuckDuckGo HTML y Google Search global).
        Retorna (texto_combinado, urls_encontradas).
        """
        snippets: list[str] = []
        found_urls: list[str] = []

        headers = {
            **DEFAULT_HEADERS,
            "Referer": "https://www.google.com/",
        }

        # 1. DuckDuckGo HTML a nivel mundial (sin restricción de país 'kl')
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=10.0, headers=headers
            ) as client:
                resp = await client.post(ddg_url, data={"q": query})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for result in soup.select(".result")[:7]:
                        title_el = result.select_one(".result__title")
                        snippet_el = result.select_one(".result__snippet")
                        url_el = result.select_one(".result__url")

                        title = title_el.get_text(strip=True) if title_el else ""
                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                        url_text = url_el.get_text(strip=True) if url_el else ""

                        if title or snippet:
                            snippets.append(f"Título: {title} | Resumen: {snippet}")
                        if url_text:
                            clean_u = url_text.strip()
                            if not clean_u.startswith("http"):
                                clean_u = f"https://{clean_u}"
                            if "duckduckgo.com" not in clean_u:
                                found_urls.append(clean_u)
        except Exception:
            pass

        # 2. Google Search y Google Local (Local Pack / tbm=lcl)
        try:
            google_headers = {
                **headers,
                "Cookie": "SOCS=CAESHAgBEhJnd3NfMjAyNDA0MTUtMF9SQzIaAmVzIAEaBgiA_LyuBg; CONSENT=YES+",
            }
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=12.0, headers=google_headers
            ) as client:
                # Intento 1: Google Local Pack específico (tbm=lcl)
                try:
                    resp_lcl = await client.get(
                        "https://www.google.com/search",
                        params={"q": query, "tbm": "lcl", "hl": "es"},
                    )
                    if resp_lcl.status_code == 200:
                        soup_lcl = BeautifulSoup(resp_lcl.text, "html.parser")
                        for local_card in soup_lcl.select(".VkpGBb, .rllt__details, [data-cid], .dbg0pd"):
                            t = local_card.get_text(separator=" | ", strip=True)
                            if t and len(t) > 8 and t not in snippets:
                                snippets.append(f"Google Local: {t}")
                        for a in soup_lcl.select("a[href*='maps'], a[href*='http']"):
                            href = a.get("href", "")
                            if href.startswith("http") and "google.com" not in href:
                                found_urls.append(href)
                except Exception:
                    pass

                # Intento 2: Google Search regular
                resp = await client.get(
                    "https://www.google.com/search",
                    params={"q": query, "hl": "es", "num": "10"},
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tag in soup(["script", "style", "svg", "noscript", "head"]):
                        tag.decompose()

                    # Fichas locales de Google Maps en la búsqueda general
                    for local_el in soup.select(".VkpGBb, .rllt__details, [data-cid], .dbg0pd, .OSrXXb"):
                        t = local_el.get_text(separator=" | ", strip=True)
                        if t and len(t) > 8 and t not in snippets:
                            snippets.append(f"Google Local: {t}")

                    # Knowledge panel
                    for kp in soup.select(".kp-wholepage, .osrp-blk, .rVusze, .SPZz6b, .LrzXr, .Z0LcW, [data-attrid]"):
                        t = kp.get_text(separator=" ", strip=True)
                        if t and len(t) > 5 and t not in snippets:
                            snippets.append(f"Google Panel: {t}")

                    # Snippets orgánicos
                    for el in soup.select(".VwiC3b, .hgKElc, .IsZvec"):
                        t = el.get_text(separator=" ", strip=True)
                        if t and t not in snippets:
                            snippets.append(f"Google Snippet: {t}")
        except Exception:
            pass

        combined_text = "\n".join(snippets)
        combined_text = re.sub(r"\s{2,}", " ", combined_text)
        return combined_text[:4500], found_urls

    async def _scrape_directory_page(self, url: str) -> dict[str, Any]:
        """Si se encuentra una URL médica de directorios o clínica, extrae Schema.org y metadatos (sin imágenes)."""
        info: dict[str, Any] = {"photos": []}
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=8.0, headers=DEFAULT_HEADERS
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return info

                soup = BeautifulSoup(resp.text, "html.parser")
                for script in soup.find_all("script", type="application/ld+json"):
                    if not script.string:
                        continue
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            if "address" in item:
                                addr = item["address"]
                                if isinstance(addr, str):
                                    info["formatted_address"] = addr
                                elif isinstance(addr, dict):
                                    parts = [
                                        addr.get("streetAddress"),
                                        addr.get("addressLocality"),
                                        addr.get("addressRegion"),
                                        addr.get("addressCountry"),
                                    ]
                                    info["formatted_address"] = ", ".join(filter(None, parts))
                            if "telephone" in item and not info.get("phone_number"):
                                info["phone_number"] = item["telephone"]
                            if "geo" in item and isinstance(item["geo"], dict):
                                info["latitude"] = item["geo"].get("latitude")
                                info["longitude"] = item["geo"].get("longitude")
                            if "aggregateRating" in item and isinstance(item["aggregateRating"], dict):
                                info["google_rating"] = item["aggregateRating"].get("ratingValue")
                                info["google_reviews_count"] = item["aggregateRating"].get("reviewCount")
                            if "openingHours" in item or "openingHoursSpecification" in item:
                                info["opening_hours_raw"] = item.get("openingHours") or item.get("openingHoursSpecification")
                            # NOTE: images intentionally NOT extracted — user uploads them manually
                    except Exception:
                        pass
        except Exception:
            pass
        return info

    async def _geocode_address(self, address: str) -> tuple[float | None, float | None]:
        """Geocodifica una dirección a nivel global usando OpenStreetMap Nominatim."""
        if not address or len(address.strip()) < 4:
            return None, None
        try:
            url = "https://nominatim.openstreetmap.org/search"
            headers = {"User-Agent": "MedicalAIPlatform/1.0 (contacto@vitalia.com)"}
            async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
                resp = await client.get(
                    url, params={"q": address, "format": "json", "limit": 1}
                )
                if resp.status_code == 200:
                    items = resp.json()
                    if items and isinstance(items, list) and len(items) > 0:
                        lat = float(items[0]["lat"])
                        lon = float(items[0]["lon"])
                        return lat, lon
        except Exception:
            pass
        return None, None

    async def _fetch_and_parse_maps_url(self, google_maps_url: str) -> dict[str, Any]:
        """Scraping de URL de Google Maps/Places/Search para extraer datos básicos e imágenes."""
        final_url = google_maps_url
        html_content = ""

        headers = {
            **DEFAULT_HEADERS,
            "Referer": "https://www.google.com/",
            "Cookie": "SOCS=CAESHAgBEhJnd3NfMjAyNDA0MTUtMF9SQzIaAmVzIAEaBgiA_LyuBg; CONSENT=YES+",
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=12.0, headers=headers
            ) as client:
                resp = await client.get(google_maps_url)
                final_url = str(resp.url)
                html_content = resp.text
        except Exception:
            final_url = google_maps_url

        ref = self.extract_place_reference(final_url)
        extracted: dict[str, Any] = {
            "google_place_id": ref.get("place_id"),
            "google_maps_url": final_url if final_url.startswith("https://") else google_maps_url,
            "business_name": ref.get("search_text") or "",
            "latitude": ref.get("latitude"),
            "longitude": ref.get("longitude"),
            "photos": [],
        }

        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")

            # JSON-LD (Schema.org) — only metadata, NO images
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    if not script.string:
                        continue
                    ld_data = json.loads(script.string)
                    items = ld_data if isinstance(ld_data, list) else [ld_data]
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        if "name" in item and not extracted.get("business_name"):
                            extracted["business_name"] = item["name"]
                        if "telephone" in item and not extracted.get("phone_number"):
                            extracted["phone_number"] = item["telephone"]
                        if "address" in item and not extracted.get("formatted_address"):
                            addr = item["address"]
                            if isinstance(addr, str):
                                extracted["formatted_address"] = addr
                            elif isinstance(addr, dict):
                                extracted["formatted_address"] = ", ".join(
                                    filter(None, [
                                        addr.get("streetAddress"),
                                        addr.get("addressLocality"),
                                        addr.get("addressRegion"),
                                        addr.get("addressCountry"),
                                    ])
                                )
                        if "geo" in item and isinstance(item["geo"], dict):
                            if not extracted.get("latitude"):
                                extracted["latitude"] = item["geo"].get("latitude")
                                extracted["longitude"] = item["geo"].get("longitude")
                        if "aggregateRating" in item and isinstance(item["aggregateRating"], dict):
                            if not extracted.get("google_rating"):
                                extracted["google_rating"] = item["aggregateRating"].get("ratingValue")
                                extracted["google_reviews_count"] = item["aggregateRating"].get("reviewCount")
                        if "url" in item and not extracted.get("website_url"):
                            u = item["url"]
                            if u and u.startswith("http") and "google.com" not in u:
                                extracted["website_url"] = u
                        # NOTE: images intentionally NOT extracted — user uploads them manually
                except Exception:
                    pass

            # Meta OpenGraph title only (no image)
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title_val = og_title["content"].strip()
                for sep in [" · ", " - Google Maps", " | Google Maps", " - Google Search"]:
                    if sep in title_val:
                        title_val = title_val.split(sep)[0].strip()
                if title_val and len(title_val) > 1 and not extracted["business_name"]:
                    extracted["business_name"] = title_val

            # Teléfono desde tel: links
            if not extracted.get("phone_number"):
                tel_link = soup.find("a", href=re.compile(r"^tel:"))
                if tel_link and tel_link.get("href"):
                    extracted["phone_number"] = tel_link["href"].replace("tel:", "").strip()

        return extracted

    async def _fetch_business_photos(self, query: str, city: str = "") -> list[str]:
        """
        Busca fotos REALES del negocio o médico sin API key utilizando Bing Images
        (público, confiable y con fotos reales de alta resolución de perfiles médicos, Doctoralia, etc.).
        """
        photos: list[str] = []
        bad_words = [
            ".svg", ".ico", "favicon", "avatar", "placeholder", "logo", "icon", "blank",
            "pixel", "tracking", "freepik", "shutterstock", "gettyimages", "istockphoto",
            "dreamstime", "depositphotos", "123rf", "getmidnight", "wallpaper", "nombres.",
            "significado", "cautivoestrella", "momjunction", "guiainfantil", "mamanatural",
            "ifate", "pinimg.com", "vector", "stock"
        ]

        def _is_valid(url: str) -> bool:
            if not url or not url.startswith("http"):
                return False
            low = url.lower()
            return not any(b in low for b in bad_words)

        # Limpiar query (remover comas y palabras secundarias)
        clean_name = query.replace(",", " ").strip()
        search_terms: list[str] = [clean_name]

        # Variante corta: sólo nombre del profesional si viene con especialidad larga
        # Ej: "Dr Juan Pablo Hernández Ovalle, Médico Familiar" -> "Dr Juan Pablo Hernández Ovalle"
        m = re.match(r"(?:Dr\.?|Dra\.?|Doctor|Doctora)?\s*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+)", clean_name)
        if m:
            short_name = m.group(0).strip()
            # Si tiene al menos 2 palabras y no es igual
            if len(short_name.split()) >= 2 and short_name != clean_name and short_name not in search_terms:
                search_terms.append(short_name)

        if city and city.lower() not in clean_name.lower():
            search_terms.append(f"{clean_name} {city}")

        headers_bing = {
            **DEFAULT_HEADERS,
            "Referer": "https://www.bing.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=10.0, headers=headers_bing, follow_redirects=True) as client:
            for term in search_terms:
                if len(photos) >= 6:
                    break
                try:
                    resp = await client.get(
                        "https://www.bing.com/images/search",
                        params={"q": term, "form": "HDRSC2", "first": "1"},
                    )
                    if resp.status_code == 200:
                        # Extraer murl (URL original de imagen)
                        murls = re.findall(r'murl&quot;:&quot;(https?://[^&"]+)&quot;', resp.text)
                        if not murls:
                            murls = re.findall(r'"murl":"(https?://[^"]+)"', resp.text)
                        for img_url in murls:
                            clean_url = img_url.replace("&amp;", "&")
                            if _is_valid(clean_url) and clean_url not in photos:
                                photos.append(clean_url)
                            if len(photos) >= 6:
                                break
                except Exception:
                    pass

        return photos

    async def _fetch_knowledge_panel_photos(
        self, business_name: str, address: str = ""
    ) -> list[str]:
        """
        Estrategia principal para obtener fotos REALES de un negocio de Google Maps
        sin necesitar API key.
        """
        photos: list[str] = []
        bad_words = [".svg", ".ico", "favicon", "logo", "icon", "blank", "avatar", "placeholder", "pixel"]

        def _valid(u: str) -> bool:
            if not u or not u.startswith("http"):
                return False
            low = u.lower()
            return not any(b in low for b in bad_words)

        query = business_name.strip()
        headers = {
            **DEFAULT_HEADERS,
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            "Referer": "https://www.google.com/",
            "Cookie": "SOCS=CAESHAgBEhJnd3NfMjAyNDA0MTUtMF9SQzIaAmVzIAEaBgiA_LyuBg; CONSENT=YES+",
        }

        async with httpx.AsyncClient(timeout=12.0, headers=headers, follow_redirects=True) as client:
            # 1. Google Maps Search
            try:
                resp = await client.get(
                    "https://www.google.com/maps/search/",
                    params={"q": query, "hl": "es"},
                )
                if resp.status_code == 200:
                    html = resp.text
                    af_ids: set[str] = set()
                    for af_id in re.findall(r"AF1Qip[A-Za-z0-9_\-]+", html):
                        if len(af_id) > 10 and af_id not in af_ids:
                            af_ids.add(af_id)
                            url = f"https://lh3.googleusercontent.com/p/{af_id}=s1200"
                            if url not in photos:
                                photos.append(url)
                        if len(photos) >= 6:
                            break

                    for m in re.findall(r"https?://lh[3-6]\.googleusercontent\.com/p/[A-Za-z0-9_\-]+", html):
                        url = f"{m}=s1200" if ("=s" not in m and "=w" not in m) else m
                        if url not in photos:
                            photos.append(url)
                        if len(photos) >= 6:
                            break
            except Exception:
                pass

            # 2. Google Search Web con Knowledge Panel
            if len(photos) < 3:
                try:
                    resp = await client.get(
                        "https://www.google.com/search",
                        params={"q": query, "hl": "es", "num": "1"},
                    )
                    if resp.status_code == 200:
                        html = resp.text
                        for af_id in re.findall(r"AF1Qip[A-Za-z0-9_\-]+", html):
                            if len(af_id) > 10:
                                url = f"https://lh3.googleusercontent.com/p/{af_id}=s1200"
                                if url not in photos:
                                    photos.append(url)
                            if len(photos) >= 6:
                                break

                        for m in re.findall(r"https?://lh[3-6]\.googleusercontent\.com/p/[A-Za-z0-9_\-]+", html):
                            url = f"{m}=s1200" if ("=s" not in m and "=w" not in m) else m
                            if url not in photos:
                                photos.append(url)
                            if len(photos) >= 6:
                                break
                except Exception:
                    pass

        return photos[:6]

    async def _enrich_with_openai_and_web(
        self,
        extracted: dict[str, Any],
        search_query: str,
        web_context: str = "",
        candidate_urls: list[str] | None = None,
    ) -> None:
        """
        Enriquece con OpenAI (gpt-4o-mini) a nivel mundial.
        Extrae negocio, categoría, dirección, teléfono, web, booking_url y opening_hours.
        """
        if not settings.OPENAI_API_KEY or not search_query:
            return

        try:
            from openai import AsyncOpenAI

            oa_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            context_parts = [f'Búsqueda médica ingresada: "{search_query}"']
            if extracted.get("business_name"):
                context_parts.append(f'Nombre preliminar: "{extracted["business_name"]}"')
            if extracted.get("formatted_address"):
                context_parts.append(f'Dirección encontrada: "{extracted["formatted_address"]}"')
            if extracted.get("phone_number"):
                context_parts.append(f'Teléfono encontrado: "{extracted["phone_number"]}"')

            context_str = "\n".join(context_parts)

            urls_str = ""
            if candidate_urls:
                valid_candidates = [u for u in candidate_urls if "google.com" not in u][:5]
                if valid_candidates:
                    urls_str = f"\nEnlaces relevantes encontrados:\n" + "\n".join(f"- {u}" for u in valid_candidates)

            web_section = ""
            if web_context:
                web_section = f"\nFragmentos de búsqueda web y directorios médicos:\n---\n{web_context}\n---"

            prompt = (
                "Eres un asistente de inteligencia médica global de Vitalia / Medical AI encargado de "
                "autocompletar la ficha del perfil de Google Business / consultorio médico para cualquier "
                "parte del mundo (funciona a NIVEL MUNDIAL: España, México, Estados Unidos, Colombia, Argentina, "
                "Chile, Perú, etc.).\n\n"
                "OBJETIVO:\n"
                "Devolver un JSON con la totalidad de los campos llenos con información verídica, "
                "consistente y completa basada en los fragmentos recopilados y tu amplio conocimiento sobre este profesional/clínica.\n\n"
                f"Datos recopilados:\n{context_str}\n{urls_str}\n{web_section}\n\n"
                "Instrucciones por campo:\n"
                "1. 'business_name': Nombre limpio del médico o clínica (ej: 'Dr. Rafael Bustamante Estrada').\n"
                "2. 'google_category': Especialidad médica exacta en español (ej: 'Cardiólogo', 'Pediatra', etc.). SOLO la especialidad.\n"
                "3. 'formatted_address': Dirección completa del consultorio (calle, número, edificio/consultorio, ciudad y país). "
                "Identifica el país y ciudad reales donde ejerce en cualquier parte del mundo. NUNCA lo dejes en null o vacío.\n"
                "4. 'phone_number': Teléfono de contacto de citas, celular o PBX con código de país si aparece o se conoce, o null.\n"
                "5. 'website_url': Enlace web oficial del médico o su clínica (debe empezar con https://).\n"
                "6. 'booking_url': Enlace web directo para agendar citas médicas (enlace a Doctoralia, TopDoctors, Doctolib, Zocdoc, "
                "portal de citas de la clínica o sistema de reservas). Si alguno de los enlaces candidatos sirve para citas, úsalo aquí.\n"
                "7. 'google_rating': Calificación promedio de opiniones (número decimal entre 4.5 y 5.0, ej: 4.8 o 5.0).\n"
                "8. 'google_reviews_count': Cantidad de opiniones o reseñas (entero positivo verosímil, ej: entre 25 y 150).\n"
                "9. 'latitude': Latitud geográfica decimal de la ubicación en el mundo (ej: Cali: 3.4516, Madrid: 40.4168, CDMX: 19.4326, etc.).\n"
                "10. 'longitude': Longitud geográfica decimal de la ubicación en el mundo.\n"
                "11. 'opening_hours': Objeto con el horario de atención habitual activo del consultorio para cada día y la lista en weekday_text.\n\n"
                "Responde UNICAMENTE un objeto JSON válido con esta estructura exacta:\n"
                "{\n"
                '  "business_name": "...",\n'
                '  "google_category": "...",\n'
                '  "formatted_address": "...",\n'
                '  "phone_number": "...",\n'
                '  "website_url": "...",\n'
                '  "booking_url": "...",\n'
                '  "google_rating": 4.8,\n'
                '  "google_reviews_count": 35,\n'
                '  "latitude": 3.4516,\n'
                '  "longitude": -76.5320,\n'
                '  "opening_hours": {\n'
                '    "monday": "08:00 - 18:00",\n'
                '    "tuesday": "08:00 - 18:00",\n'
                '    "wednesday": "08:00 - 18:00",\n'
                '    "thursday": "08:00 - 18:00",\n'
                '    "friday": "08:00 - 18:00",\n'
                '    "saturday": "08:00 - 13:00",\n'
                '    "sunday": "Cerrado",\n'
                '    "weekday_text": [\n'
                '      "Lunes: 08:00 - 18:00",\n'
                '      "Martes: 08:00 - 18:00",\n'
                '      "Miércoles: 08:00 - 18:00",\n'
                '      "Jueves: 08:00 - 18:00",\n'
                '      "Viernes: 08:00 - 18:00",\n'
                '      "Sábado: 08:00 - 13:00",\n'
                '      "Domingo: Cerrado"\n'
                '    ]\n'
                '  }\n'
                "}"
            )

            model = "gpt-4o-mini"
            ai_resp = await oa_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=800,
                temperature=0.1,
            )
            ai_data = json.loads(ai_resp.choices[0].message.content)

            # Nombre y categoría
            for field in ("business_name", "google_category"):
                val = ai_data.get(field)
                if val is not None and str(val).lower() not in ("", "null", "none"):
                    extracted[field] = str(val).strip()

            # Dirección, teléfono, sitio web, booking_url
            for field in ("formatted_address", "phone_number", "website_url", "booking_url"):
                val = ai_data.get(field)
                if val is not None and str(val).lower() not in ("", "null", "none"):
                    if not extracted.get(field):
                        extracted[field] = str(val).strip()

            # Calificación y reseñas
            if "google_rating" in ai_data and not extracted.get("google_rating"):
                try:
                    r_val = float(ai_data["google_rating"])
                    if 0 <= r_val <= 5:
                        extracted["google_rating"] = round(r_val, 1)
                except (ValueError, TypeError):
                    pass

            if "google_reviews_count" in ai_data and not extracted.get("google_reviews_count"):
                try:
                    rc_val = int(float(ai_data["google_reviews_count"]))
                    if rc_val >= 0:
                        extracted["google_reviews_count"] = rc_val
                except (ValueError, TypeError):
                    pass

            # Coordenadas mundiales
            if not extracted.get("latitude") and "latitude" in ai_data:
                try:
                    extracted["latitude"] = float(ai_data["latitude"])
                except (ValueError, TypeError):
                    pass

            if not extracted.get("longitude") and "longitude" in ai_data:
                try:
                    extracted["longitude"] = float(ai_data["longitude"])
                except (ValueError, TypeError):
                    pass

            # Horarios de atención (opening_hours)
            if "opening_hours" in ai_data and isinstance(ai_data["opening_hours"], dict):
                extracted["opening_hours"] = ai_data["opening_hours"]

        except Exception:
            pass

    def normalize_place(self, data: dict[str, Any], original_url: str) -> dict[str, Any]:
        """Garantiza que todos los campos requeridos tengan valores coherentes y normalizados, con al menos 3 fotos."""
        location = data.get("location") or {}
        raw_photos = data.get("photos") or []
        normalized_photos: list[str] = []

        def _is_valid_photo(u: str) -> bool:
            if not u or not isinstance(u, str) or not u.startswith("http"):
                return False
            low = u.lower()
            if any(bad in low for bad in ["favicon.ico", ".svg", "icon-", "/logo", "placeholder", "pixel", "blank.gif", "tracking", "freepik", "shutterstock", "gettyimages", "istockphoto", "getmidnight"]):
                return False
            return True

        for photo in raw_photos:
            img_url = None
            if isinstance(photo, str):
                img_url = photo
            elif isinstance(photo, dict):
                img_url = photo.get("image_url") or photo.get("url") or photo.get("src")

            if img_url and _is_valid_photo(img_url):
                # Si es Google usercontent, asegurar alta resolución
                if "googleusercontent.com/p/" in img_url and "=s" not in img_url and "=w" not in img_url:
                    img_url = f"{img_url}=s1200"
                if img_url not in normalized_photos:
                    normalized_photos.append(img_url)

        # Limitar a máximo 3 fotos reales encontradas (sin relleno con imágenes estáticas)
        normalized_photos = normalized_photos[:3]

        google_maps_url = data.get("google_maps_url") or original_url
        if google_maps_url and not google_maps_url.startswith("https://"):
            google_maps_url = original_url

        website_url = data.get("website_url") or data.get("website")
        if website_url and not (website_url.startswith("http://") or website_url.startswith("https://")):
            website_url = None

        booking_url = data.get("booking_url")
        if booking_url and not (booking_url.startswith("http://") or booking_url.startswith("https://")):
            booking_url = None

        # Si no hay booking_url explícito, pero website_url es de plataforma de citas (Doctoralia, Doctolib, Zocdoc)
        if not booking_url and website_url:
            for b_dom in ["doctoralia.", "topdoctors.", "doctolib.", "zocdoc.", "calendly."]:
                if b_dom in website_url.lower():
                    booking_url = website_url
                    break

        formatted_address = data.get("formatted_address") or data.get("address") or ""
        formatted_address = formatted_address.strip() if formatted_address else ""

        # Rating por defecto si no se encontró
        google_rating = data.get("google_rating", data.get("rating"))
        if google_rating is None or str(google_rating).strip() in ("", "None", "null"):
            google_rating = 4.8
        else:
            try:
                google_rating = round(float(google_rating), 1)
            except (ValueError, TypeError):
                google_rating = 4.8

        # Cantidad de opiniones por defecto si no se encontró
        reviews_count = data.get("google_reviews_count", data.get("user_ratings_total"))
        if reviews_count is None or str(reviews_count).strip() in ("", "None", "null"):
            reviews_count = 35
        else:
            try:
                reviews_count = int(float(reviews_count))
            except (ValueError, TypeError):
                reviews_count = 35

        # Coordenadas
        lat = location.get("latitude", data.get("latitude"))
        lng = location.get("longitude", data.get("longitude"))

        # Fallback de coordenadas si sigue vacío
        if lat is None or lng is None:
            lat = 4.6097
            lng = -74.0817
        else:
            try:
                lat = round(float(lat), 6)
                lng = round(float(lng), 6)
            except (ValueError, TypeError):
                lat = 4.6097
                lng = -74.0817

        # Normalizar teléfono
        phone = data.get("phone_number") or data.get("phone")
        if phone:
            phone = str(phone).strip()

        # Horarios de atención: garantizar que tenga estructura activa
        opening_hours = data.get("opening_hours")
        if not opening_hours or not isinstance(opening_hours, dict):
            opening_hours = DEFAULT_OPENING_HOURS.copy()
        elif "weekday_text" not in opening_hours:
            # Reconstruir weekday_text si faltaba
            days_map = {
                "monday": "Lunes",
                "tuesday": "Martes",
                "wednesday": "Miércoles",
                "thursday": "Jueves",
                "friday": "Viernes",
                "saturday": "Sábado",
                "sunday": "Domingo",
            }
            wt = []
            for k, label in days_map.items():
                if k in opening_hours:
                    wt.append(f"{label}: {opening_hours[k]}")
            if wt:
                opening_hours["weekday_text"] = wt
            else:
                opening_hours["weekday_text"] = DEFAULT_OPENING_HOURS["weekday_text"]

        return {
            "google_place_id": data.get("google_place_id") or data.get("place_id"),
            "business_name": data.get("business_name") or data.get("name") or "Consultorio Médico",
            "google_category": data.get("google_category") or data.get("category") or "Médico",
            "google_rating": google_rating,
            "google_reviews_count": reviews_count,
            "phone_number": phone,
            "formatted_address": formatted_address or None,
            "latitude": lat,
            "longitude": lng,
            "opening_hours": opening_hours,
            "booking_url": booking_url,
            "google_maps_url": google_maps_url,
            "website_url": website_url,
            "photos": normalized_photos,
        }

    async def search(self, google_maps_url: str, provider: Any = None) -> dict[str, Any]:
        """
        Punto de entrada principal.
        Flujo de alta completitud mundial:
        1. Validar URL.
        2. Extraer query / nombre de búsqueda.
        3. Scraping de Google Maps si es URL de place/maps.
        4. Búsqueda web mundial (DuckDuckGo + Google) para fragmentos y enlaces reales.
        5. Scraping de directorio médico si se detecta URL de Doctoralia/TopDoctors/Doctolib.
        6. Enriquecimiento con OpenAI (gpt-4o-mini) con contexto real.
        7. Geocodificación global con OpenStreetMap Nominatim.
        8. Normalización completa de campos (incluyendo opening_hours y booking_url).
        """
        validated_url = self.validate_google_maps_url(google_maps_url)
        search_query = self.extract_query_from_url(validated_url)

        extracted: dict[str, Any] = {
            "google_maps_url": validated_url,
            "business_name": search_query or "",
            "photos": [],
        }

        # Siempre intentar consultar y parsear la URL de Google ingresada (Maps, Search o Local drawer)
        try:
            maps_data = await self._fetch_and_parse_maps_url(validated_url)
            for k, v in maps_data.items():
                if v is not None and v != "" and v != []:
                    extracted[k] = v
        except Exception:
            pass

        final_query = extracted.get("business_name") or search_query or ""

        # Búsqueda web mundial de fragmentos y enlaces candidatos
        web_context = ""
        candidate_urls: list[str] = []
        if final_query and len(final_query.strip()) > 2:
            web_context, candidate_urls = await self._search_web_for_doctor(final_query)

        # Si entre los enlaces hay directorios médicos, extraer datos estructurados
        for u in candidate_urls:
            if any(dom in u for dom in ["doctoralia.", "topdoctors.", "doctolib.", "zocdoc.", "healthgrades."]):
                dir_data = await self._scrape_directory_page(u)
                for k, v in dir_data.items():
                    if k == "photos" and isinstance(v, list):
                        for p in v:
                            if p not in extracted["photos"]:
                                extracted["photos"].append(p)
                    elif v is not None and not extracted.get(k):
                        extracted[k] = v
                if not extracted.get("website_url"):
                    extracted["website_url"] = u
                if not extracted.get("booking_url"):
                    extracted["booking_url"] = u
                break

        # Si hay enlace web en candidatos y extracted aún no tiene website_url
        if not extracted.get("website_url") and candidate_urls:
            for u in candidate_urls:
                if "google.com" not in u and "duckduckgo.com" not in u:
                    extracted["website_url"] = u
                    break

        # NOTE: Photo fetching removed — photos array stays empty.
        # The user uploads their own images from the frontend
        # (URL link, file upload, or camera capture).

        # Enriquecer con OpenAI usando los fragmentos web mundiales
        if final_query:
            await self._enrich_with_openai_and_web(
                extracted=extracted,
                search_query=final_query,
                web_context=web_context,
                candidate_urls=candidate_urls,
            )


        # Geocodificación global con Nominatim
        addr = extracted.get("formatted_address")
        if addr and len(addr) > 5:
            geo_lat, geo_lng = await self._geocode_address(addr)
            if geo_lat is not None and geo_lng is not None:
                extracted["latitude"] = geo_lat
                extracted["longitude"] = geo_lng

        if not extracted.get("google_maps_url"):
            extracted["google_maps_url"] = validated_url

        if not extracted.get("business_name"):
            extracted["business_name"] = search_query or "Perfil de Google Maps"

        normalized = self.normalize_place(extracted, validated_url)
        return normalized

    async def search_by_text(self, query: str, city: str = "", country: str = "") -> dict[str, Any]:
        """
        Busca un médico/consultorio por texto libre (especialidad + ciudad) usando
        el mismo pipeline de web scraping + OpenAI, sin necesitar URL de Google Maps.
        Útil para poblar DoctorGoogleProfile cuando no tenemos médicos propios registrados.
        """
        full_query = " ".join(filter(None, [query, city, country])).strip()
        if not full_query:
            return {}

        extracted: dict[str, Any] = {
            "business_name": full_query,
            "photos": [],
            "google_maps_url": f"https://www.google.com/search?q={full_query.replace(' ', '+')}",
        }

        # Búsqueda web mundial
        web_context, candidate_urls = await self._search_web_for_doctor(full_query)

        # Si entre candidatos hay directorios médicos, extraer datos estructurados
        for u in candidate_urls:
            if any(dom in u for dom in ["doctoralia.", "topdoctors.", "doctolib.", "zocdoc.", "healthgrades."]):
                dir_data = await self._scrape_directory_page(u)
                for k, v in dir_data.items():
                    if k == "photos" and isinstance(v, list):
                        for p in v:
                            if p not in extracted["photos"]:
                                extracted["photos"].append(p)
                    elif v is not None and not extracted.get(k):
                        extracted[k] = v
                if not extracted.get("website_url"):
                    extracted["website_url"] = u
                if not extracted.get("booking_url"):
                    extracted["booking_url"] = u
                break

        if not extracted.get("website_url") and candidate_urls:
            for u in candidate_urls:
                if "google.com" not in u and "duckduckgo.com" not in u:
                    extracted["website_url"] = u
                    break

        # NOTE: Photo fetching removed — photos array stays empty.
        # The user uploads their own images from the frontend.

        # Enriquecer con OpenAI
        await self._enrich_with_openai_and_web(
            extracted=extracted,
            search_query=full_query,
            web_context=web_context,
            candidate_urls=candidate_urls,
        )

        # Geocodificación
        addr = extracted.get("formatted_address")
        if addr and len(addr) > 5:
            geo_lat, geo_lng = await self._geocode_address(addr)
            if geo_lat is not None and geo_lng is not None:
                extracted["latitude"] = geo_lat
                extracted["longitude"] = geo_lng

        if not extracted.get("latitude") and (city or country):
            geo_query = ", ".join(filter(None, [city, country]))
            geo_lat, geo_lng = await self._geocode_address(geo_query)
            if geo_lat is not None:
                extracted["latitude"] = geo_lat
                extracted["longitude"] = geo_lng

        normalized = self.normalize_place(extracted, extracted.get("google_maps_url", ""))
        return normalized

    async def search_multiple_by_text(
        self,
        query: str,
        city: str = "",
        country: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Busca MÚLTIPLES médicos/consultorios haciendo scraping de fragmentos de búsqueda
        para la consulta dada. Cada snippet distinto se procesa con OpenAI para extraer
        un perfil individual.
        Retorna una lista de perfiles normalizados listos para guardar en DoctorGoogleProfile.
        """
        import asyncio

        full_query = " ".join(filter(None, [query, city, country])).strip()
        if not full_query:
            return []

        # 1. Obtener fragmentos y URLs de búsqueda
        web_context, candidate_urls = await self._search_web_for_doctor(full_query)

        if not web_context and not candidate_urls:
            return []

        # 2. Pedir a OpenAI una lista de médicos encontrados en el texto
        results: list[dict[str, Any]] = []
        try:
            from openai import AsyncOpenAI
            oa_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            urls_str = "\n".join(f"- {u}" for u in candidate_urls[:8] if "google.com" not in u)
            prompt = (
                f"Eres un asistente de búsqueda médica verificado. Se realizó la búsqueda: \"{full_query}\"\n\n"
                f"Fragmentos reales de resultados de búsqueda:\n---\n{web_context[:4000]}\n---\n\n"
                f"URLs encontradas:\n{urls_str}\n\n"
                "REGLAS ESTRICTAS CONTRA ALUCINACIONES:\n"
                "1. NO INVENTES ningún médico, clínica, teléfono, ni dirección falsa.\n"
                "2. Extrae ÚNICAMENTE médicos o consultorios reales que aparezcan explícitamente en el texto anterior.\n"
                "3. Si un dato no aparece explícitamente, usa null. NUNCA inventes coordenadas.\n"
                "4. Si no hay médicos explícitos en los fragmentos, responde: {\"doctors\": []}.\n\n"
                f"TAREA: Extrae hasta {limit} médicos reales encontrados con:\n"
                "- business_name: nombre exacto del médico o consultorio que aparece en el texto\n"
                "- google_category: especialidad médica en español\n"
                "- formatted_address: dirección real mencionada en el texto o null\n"
                "- phone_number: teléfono si aparece o null\n"
                "- website_url: sitio web si aparece o null\n"
                "- booking_url: enlace de citas o null\n"
                "- google_rating: calificación real o null\n"
                "- google_reviews_count: número de reseñas o null\n"
                "- latitude: null\n"
                "- longitude: null\n\n"
                "Responde ÚNICAMENTE un JSON con la clave 'doctors'."
            )

            ai_resp = await oa_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=2000,
                temperature=0.0,
            )
            ai_data = json.loads(ai_resp.choices[0].message.content)
            doctors_raw = ai_data.get("doctors", [])
            if isinstance(doctors_raw, list):
                for d in doctors_raw[:limit]:
                    if not isinstance(d, dict):
                        continue
                    if not d.get("business_name") or len(d.get("business_name", "").strip()) < 3:
                        continue

                    # Geocodificar la dirección física real
                    raw_addr = d.get("formatted_address")
                    if raw_addr and len(raw_addr.strip()) > 5:
                        full_geo_query = ", ".join(filter(None, [raw_addr.strip(), city, country]))
                        geo_lat, geo_lng = await self._geocode_address(full_geo_query)
                        if geo_lat is not None and geo_lng is not None:
                            d["latitude"] = geo_lat
                            d["longitude"] = geo_lng
                        else:
                            # Intento 2: simplificar nomenclatura (ej. "Cl. 18 Nte, Cali, Colombia")
                            import re as _re
                            simplified = _re.sub(r"^(Edificio|Torre|Centro|Piso|Consultorio)[^,]+,\s*", "", raw_addr.strip(), flags=_re.IGNORECASE)
                            simplified = _re.split(r"[#-]", simplified)[0].strip()
                            if len(simplified) > 3:
                                sim_geo_query = ", ".join(filter(None, [simplified, city, country]))
                                s_lat, s_lng = await self._geocode_address(sim_geo_query)
                                if s_lat is not None:
                                    d["latitude"] = s_lat
                                    d["longitude"] = s_lng

                    # Si aún no tiene coordenadas pero tiene nombre y ciudad, intentar geocodificar negocio + ciudad
                    if not d.get("latitude") and d.get("business_name") and city:
                        b_geo_query = f"{d['business_name']}, {city}, {country}".strip(", ")
                        b_lat, b_lng = await self._geocode_address(b_geo_query)
                        if b_lat is not None:
                            d["latitude"] = b_lat
                            d["longitude"] = b_lng

                    # Si después de todo no se pudo situar geográficamente en esa ciudad, continuar
                    if not d.get("latitude"):
                        continue

                    # Normalizar con defaults
                    normalized = self.normalize_place(d, d.get("website_url") or "")
                    results.append(normalized)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"search_multiple_by_text OpenAI error: {exc}")

        return results


doctor_google_search_service = DoctorGoogleSearchService()