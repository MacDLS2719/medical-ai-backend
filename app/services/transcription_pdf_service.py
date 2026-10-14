import textwrap
import unicodedata
from datetime import datetime
from typing import Any


def create_clinical_report_pdf(
    service_type: str,
    specialty: str = "Medicina General",
    date_str: str | None = None,
    patient_name: str | None = None,
    patient_gender: str | None = None,
    doctor_name: str | None = None,
    summary: str = "",
) -> bytes:
    """
    Genera el INFORME MÉDICO oficial en formato PDF.
    Estructura:
      - Encabezado: Servicio, Especialidad, Fecha, Médico
      - DATOS DEL PACIENTE: Nombre, Sexo
      - MOTIVO DE CONSULTA
      - EXPLORACIÓN FÍSICA
      - IMPRESIÓN DIAGNÓSTICA
      - PLAN Y TRATAMIENTO
    """
    builder = _PDFDocumentBuilder()

    service_label = (service_type or "Videollamada").strip()
    specialty_label = (specialty or "Medicina General").strip()
    date_label = date_str or datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    patient_name_label = (patient_name or "No especificado").strip()
    patient_gender_label = (patient_gender or "No especificado").strip()
    doctor_name_label = (doctor_name or "Médico tratante").strip()

    sections = _parse_clinical_sections(summary)

    # Portada / Bloque Superior en Página 1
    builder.draw_accent_bar(color=(0.14, 0.38, 0.74))  # Azul médico

    builder.draw_header_title(
        title="INFORME MÉDICO",
        badge="MIVOR · SALUD DIGITAL",
        accent_color=(0.14, 0.38, 0.74),
    )

    # Tarjeta de Datos de la Consulta
    builder.draw_metadata_card(
        items=[
            ("Servicio:", service_label),
            ("Especialidad:", specialty_label),
            ("Fecha:", date_label),
            ("Médico tratante:", doctor_name_label),
        ]
    )

    builder.add_spacing(10)

    # Tarjeta de Datos del Paciente
    builder.draw_patient_card(
        patient_name=patient_name_label,
        patient_gender=patient_gender_label,
    )

    builder.add_spacing(14)

    # 4 Secciones Clínicas Principales
    clinical_blocks = [
        ("MOTIVO DE CONSULTA", sections.get("motivo", "No referido durante la consulta.")),
        ("EXPLORACIÓN FÍSICA", sections.get("exploracion", "No referida o no evaluada en esta sesión.")),
        ("IMPRESIÓN DIAGNÓSTICA", sections.get("diagnostico", "No especificada.")),
        ("PLAN Y TRATAMIENTO", sections.get("plan", "No especificado.")),
    ]

    for section_title, section_body in clinical_blocks:
        builder.draw_clinical_section(
            title=section_title,
            body=section_body,
            accent_color=(0.14, 0.38, 0.74),
        )

    return builder.build(
        footer_left="Mivor Salud Digital · Informe Clínico Confidencial",
        header_title="INFORME MÉDICO",
    )


def create_transcription_pdf(
    service_type: str,
    specialty: str = "Medicina General",
    date_str: str | None = None,
    patient_name: str | None = None,
    doctor_name: str | None = None,
    transcript: str = "",
) -> bytes:
    """
    Genera el PDF con la TRANSCRIPCIÓN COMPLETA del audio / consulta médica.
    """
    builder = _PDFDocumentBuilder()

    service_label = (service_type or "Videollamada").strip()
    specialty_label = (specialty or "Medicina General").strip()
    date_label = date_str or datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    patient_name_label = (patient_name or "No especificado").strip()
    doctor_name_label = (doctor_name or "Médico tratante").strip()

    # Barra acentuada morado/violeta
    builder.draw_accent_bar(color=(0.43, 0.28, 0.82))

    builder.draw_header_title(
        title="TRANSCRIPCIÓN DE CONSULTA",
        badge="MIVOR · REGISTRO DE AUDIO",
        accent_color=(0.43, 0.28, 0.82),
    )

    builder.draw_metadata_card(
        items=[
            ("Servicio:", service_label),
            ("Especialidad:", specialty_label),
            ("Fecha:", date_label),
            ("Paciente:", patient_name_label),
            ("Médico:", doctor_name_label),
        ]
    )

    builder.add_spacing(14)

    builder.draw_clinical_section(
        title="TRANSCRIPCIÓN COMPLETA DEL AUDIO",
        body=transcript or "No hay transcripción disponible.",
        accent_color=(0.43, 0.28, 0.82),
        line_width=86,
    )

    return builder.build(
        footer_left="Mivor · Transcripción de Audio de Sesión",
        header_title="TRANSCRIPCIÓN DE CONSULTA",
    )


def create_transcription_report_pdf(summary: str, transcript: str) -> bytes:
    """
    Función de compatibilidad: genera informe clínico y transcripción completa.
    """
    return create_clinical_report_pdf(
        service_type="Consulta Médica",
        specialty="Medicina General",
        summary=summary,
    )


# ==============================================================================
# PARSERS Y HELPERS
# ==============================================================================

def _parse_clinical_sections(text: str) -> dict[str, str]:
    """
    Extrae las 4 secciones estándar del texto estructurado de IA:
      - MOTIVO DE CONSULTA
      - EXPLORACIÓN FÍSICA
      - IMPRESIÓN DIAGNÓSTICA
      - PLAN Y TRATAMIENTO
    Si el texto no contiene los marcadores, distribuye el contenido adecuadamente.
    """
    if not text:
        return {
            "motivo": "No registrado.",
            "exploracion": "No referida en esta sesión.",
            "diagnostico": "No especificado.",
            "plan": "No especificado.",
        }

    normalized = text.replace("\r\n", "\n")
    lower = normalized.lower()

    markers = [
        ("motivo", ["motivo de consulta", "motivo de la consulta", "motivo:"]),
        ("exploracion", ["exploración física", "exploracion fisica", "examen físico", "examen fisico"]),
        ("diagnostico", ["impresión diagnóstica", "impresion diagnostica", "diagnóstico", "diagnostico"]),
        ("plan", ["plan y tratamiento", "plan de tratamiento", "plan terapéutico", "tratamiento"]),
    ]

    positions: list[tuple[int, str, int]] = []
    for key, aliases in markers:
        for alias in aliases:
            pos = lower.find(alias)
            if pos != -1:
                # Saltear la palabra clave
                end_pos = pos + len(alias)
                # Omitir dos puntos o saltos de línea inmediatamente después
                while end_pos < len(normalized) and normalized[end_pos] in (":", " ", "\t", "-"):
                    end_pos += 1
                positions.append((pos, key, end_pos))
                break

    if not positions:
        # Texto plano sin secciones identificables
        return {
            "motivo": text.strip(),
            "exploracion": "No referida o no evaluada en esta sesión.",
            "diagnostico": "Revisar detalles en la consulta.",
            "plan": "Revisar indicaciones en la consulta.",
        }

    positions.sort(key=lambda item: item[0])

    extracted: dict[str, str] = {}
    for i, (_, key, start_idx) in enumerate(positions):
        next_pos = positions[i + 1][0] if i + 1 < len(positions) else len(normalized)
        content = normalized[start_idx:next_pos].strip()
        extracted[key] = content if content else "No referido en esta sesión."

    # Rellenar faltantes
    if "motivo" not in extracted:
        extracted["motivo"] = "No referido."
    if "exploracion" not in extracted:
        extracted["exploracion"] = "No referida o no evaluada en esta sesión."
    if "diagnostico" not in extracted:
        extracted["diagnostico"] = "No especificado."
    if "plan" not in extracted:
        extracted["plan"] = "No especificado."

    return extracted


def _wrap_text(text: str, width: int = 86) -> list[str]:
    paragraphs = text.splitlines() or [""]
    lines = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(paragraph, width=width, replace_whitespace=True) or [""]
        lines.extend(wrapped)
    return lines


def _pdf_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    encoded = normalized.encode("cp1252", errors="replace")
    text = encoded.decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


# ==============================================================================
# MOTOR DE CONSTRUCCIÓN PDF 1.4
# ==============================================================================

class _PDFDocumentBuilder:
    PAGE_WIDTH = 612
    PAGE_HEIGHT = 792
    LEFT_MARGIN = 45
    RIGHT_MARGIN = 45
    CONTENT_WIDTH = 522  # 612 - 45 - 45
    TOP_MARGIN = 750
    BOTTOM_MARGIN = 55

    def __init__(self):
        self.pages: list[list[str]] = [[]]
        self.current_y = self.TOP_MARGIN

    @property
    def current_page_commands(self) -> list[str]:
        return self.pages[-1]

    def new_page(self, header_title: str = "INFORME MÉDICO"):
        self.pages.append([])
        self.current_y = self.TOP_MARGIN

        # Encabezado para páginas subsiguientes
        cmds = self.current_page_commands
        cmds.extend([
            "q",
            "0.5 0.55 0.65 rg",
            "BT",
            "/F1 8 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} 758 Tm",
            f"({_pdf_text(header_title + ' (Continuación)')}) Tj",
            "ET",
            "0.88 0.90 0.94 RG",
            "0.5 w",
            f"{self.LEFT_MARGIN} 750 m {self.LEFT_MARGIN + self.CONTENT_WIDTH} 750 l S",
            "Q",
        ])
        self.current_y = 730

    def ensure_space(self, height: float, header_title: str = "INFORME MÉDICO"):
        if self.current_y - height < self.BOTTOM_MARGIN:
            self.new_page(header_title)

    def add_spacing(self, pts: float):
        self.current_y -= pts

    def draw_accent_bar(self, color: tuple[float, float, float] = (0.14, 0.38, 0.74)):
        r, g, b = color
        self.current_page_commands.extend([
            "q",
            f"{r:.3f} {g:.3f} {b:.3f} rg",
            f"{self.LEFT_MARGIN} {self.current_y} {self.CONTENT_WIDTH} 4 re f",
            "Q",
        ])
        self.current_y -= 16

    def draw_header_title(
        self,
        title: str,
        badge: str = "MIVOR · SALUD DIGITAL",
        accent_color: tuple[float, float, float] = (0.14, 0.38, 0.74),
    ):
        cmds = self.current_page_commands
        r, g, b = accent_color

        # Badge superior
        cmds.extend([
            "q",
            f"{r:.3f} {g:.3f} {b:.3f} rg",
            "BT",
            "/F2 8 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} {self.current_y} Tm",
            f"({_pdf_text(badge)}) Tj",
            "ET",
            "Q",
        ])
        self.current_y -= 18

        # Título principal
        cmds.extend([
            "q",
            "0.08 0.12 0.22 rg",
            "BT",
            "/F2 20 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} {self.current_y} Tm",
            f"({_pdf_text(title)}) Tj",
            "ET",
            "Q",
        ])
        self.current_y -= 18

    def draw_metadata_card(self, items: list[tuple[str, str]]):
        """
        Dibuja una cuadrícula de datos generales de la consulta (Servicio, Especialidad, etc.)
        """
        card_height = 42
        self.ensure_space(card_height + 10)
        y_box = self.current_y - card_height

        cmds = self.current_page_commands
        # Fondo gris claro / azul tenue
        cmds.extend([
            "q",
            "0.965 0.975 0.990 rg",
            f"{self.LEFT_MARGIN} {y_box} {self.CONTENT_WIDTH} {card_height} re f",
            "0.880 0.905 0.940 RG",
            "0.8 w",
            f"{self.LEFT_MARGIN} {y_box} {self.CONTENT_WIDTH} {card_height} re s",
            "Q",
        ])

        # Organizar en 2 columnas
        col_width = self.CONTENT_WIDTH / 2
        for idx, (label, val) in enumerate(items):
            col = idx % 2
            row = idx // 2
            x_pos = self.LEFT_MARGIN + 12 + (col * col_width)
            y_pos = self.current_y - 15 - (row * 16)

            cmds.extend([
                "BT",
                "/F2 9 Tf",
                "0.25 0.30 0.40 rg",
                f"1 0 0 1 {x_pos} {y_pos} Tm",
                f"({_pdf_text(label)}) Tj",
                "/F1 9 Tf",
                "0.10 0.14 0.22 rg",
                f"1 0 0 1 {x_pos + 80} {y_pos} Tm",
                f"({_pdf_text(val)}) Tj",
                "ET",
            ])

        self.current_y = y_box

    def draw_patient_card(self, patient_name: str, patient_gender: str):
        """
        Dibuja la sección destacada de DATOS DEL PACIENTE:
        Nombre y Sexo.
        """
        card_height = 46
        self.ensure_space(card_height + 10)
        y_box = self.current_y - card_height

        cmds = self.current_page_commands
        # Fondo blanco con borde sutil y acento izquierdo
        cmds.extend([
            "q",
            "0.985 0.990 1.0 rg",
            f"{self.LEFT_MARGIN} {y_box} {self.CONTENT_WIDTH} {card_height} re f",
            "0.82 0.86 0.93 RG",
            "0.8 w",
            f"{self.LEFT_MARGIN} {y_box} {self.CONTENT_WIDTH} {card_height} re s",
            # Barra acentuada izquierda
            "0.14 0.38 0.74 rg",
            f"{self.LEFT_MARGIN} {y_box} 4 {card_height} re f",
            "Q",
        ])

        # Título de la tarjeta
        cmds.extend([
            "BT",
            "/F2 9 Tf",
            "0.14 0.38 0.74 rg",
            f"1 0 0 1 {self.LEFT_MARGIN + 14} {self.current_y - 14} Tm",
            f"({_pdf_text('DATOS DEL PACIENTE')}) Tj",
            "ET",
        ])

        # Nombre y Sexo
        cmds.extend([
            "BT",
            "/F2 9.5 Tf",
            "0.25 0.30 0.40 rg",
            f"1 0 0 1 {self.LEFT_MARGIN + 14} {self.current_y - 32} Tm",
            f"({_pdf_text('Nombre:')}) Tj",
            "/F2 9.5 Tf",
            "0.08 0.12 0.22 rg",
            f"1 0 0 1 {self.LEFT_MARGIN + 62} {self.current_y - 32} Tm",
            f"({_pdf_text(patient_name)}) Tj",
            "/F2 9.5 Tf",
            "0.25 0.30 0.40 rg",
            f"1 0 0 1 {self.LEFT_MARGIN + 320} {self.current_y - 32} Tm",
            f"({_pdf_text('Sexo:')}) Tj",
            "/F1 9.5 Tf",
            "0.08 0.12 0.22 rg",
            f"1 0 0 1 {self.LEFT_MARGIN + 355} {self.current_y - 32} Tm",
            f"({_pdf_text(patient_gender)}) Tj",
            "ET",
        ])

        self.current_y = y_box

    def draw_clinical_section(
        self,
        title: str,
        body: str,
        accent_color: tuple[float, float, float] = (0.14, 0.38, 0.74),
        line_width: int = 86,
    ):
        """
        Dibuja un encabezado de sección clínica con su cuerpo de texto envuelto.
        Si el contenido supera el espacio restante, se pagina limpiamente.
        """
        lines = _wrap_text(body, width=line_width)
        r, g, b = accent_color

        # Encabezado de sección
        self.ensure_space(32)
        cmds = self.current_page_commands

        cmds.extend([
            "q",
            # Pequeño marcador decorativo a la izquierda del título
            f"{r:.3f} {g:.3f} {b:.3f} rg",
            f"{self.LEFT_MARGIN} {self.current_y - 10} 3 11 re f",
            "BT",
            "/F2 10.5 Tf",
            "0.10 0.15 0.25 rg",
            f"1 0 0 1 {self.LEFT_MARGIN + 10} {self.current_y - 9} Tm",
            f"({_pdf_text(title)}) Tj",
            "ET",
            # Línea separadora tenue bajo el título
            "0.90 0.92 0.95 RG",
            "0.5 w",
            f"{self.LEFT_MARGIN + 10} {self.current_y - 14} m {self.LEFT_MARGIN + self.CONTENT_WIDTH} {self.current_y - 14} l S",
            "Q",
        ])
        self.current_y -= 26

        # Líneas de texto del cuerpo
        for line in lines:
            if not line:
                self.current_y -= 6
                continue

            self.ensure_space(14)
            cmds = self.current_page_commands
            escaped = _pdf_text(line)
            cmds.extend([
                "BT",
                "/F1 9.5 Tf",
                "0.18 0.22 0.30 rg",
                f"1 0 0 1 {self.LEFT_MARGIN + 10} {self.current_y} Tm",
                f"({escaped}) Tj",
                "ET",
            ])
            self.current_y -= 13.5

        self.current_y -= 10

    def build(self, footer_left: str = "", header_title: str = "INFORME MÉDICO") -> bytes:
        total_pages = len(self.pages)

        # Preparar objetos PDF
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",  # 2: Pages (se actualiza abajo)
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",  # 3: F1
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",  # 4: F2
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>",  # 5: F3
        ]

        page_object_ids = []
        for page_idx, cmds in enumerate(self.pages, start=1):
            page_id = len(objects) + 1
            content_id = page_id + 1
            page_object_ids.append(page_id)

            # Agregar pie de página en cada página
            footer_cmds = [
                "q",
                "0.88 0.90 0.94 RG",
                "0.5 w",
                f"{self.LEFT_MARGIN} 42 m {self.LEFT_MARGIN + self.CONTENT_WIDTH} 42 l S",
                "BT",
                "/F1 8 Tf",
                "0.50 0.55 0.65 rg",
                f"1 0 0 1 {self.LEFT_MARGIN} 30 Tm",
                f"({_pdf_text(footer_left)}) Tj",
                f"1 0 0 1 {self.LEFT_MARGIN + self.CONTENT_WIDTH - 65} 30 Tm",
                f"({_pdf_text(f'Página {page_idx} de {total_pages}')}) Tj",
                "ET",
                "Q",
            ]
            full_stream_cmds = cmds + footer_cmds
            stream_bytes = "\n".join(full_stream_cmds).encode("latin-1")

            objects.append(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.PAGE_WIDTH} {self.PAGE_HEIGHT}] "
                    f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode("ascii")
            )
            objects.append(
                b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n"
                + stream_bytes
                + b"\nendstream"
            )

        kids = " ".join(f"{object_id} 0 R" for object_id in page_object_ids)
        objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>".encode("ascii")

        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for object_id, body in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
            pdf.extend(body)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

        pdf.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF"
            ).encode("ascii")
        )
        return bytes(pdf)
