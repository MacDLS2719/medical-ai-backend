import html
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime

from app.services.transcription_pdf_service import _parse_clinical_sections


def _escape(text: str) -> str:
    """Escapa caracteres especiales para XML seguro en Word OpenXML."""
    if not text:
        return ""
    return html.escape(str(text), quote=False).replace('"', "&quot;").replace("'", "&apos;")


def _build_docx_xml(
    title: str,
    subtitle: str,
    metadata: list[tuple[str, str]],
    sections: list[tuple[str, str, str]],  # (title, content, color_hex)
) -> str:
    """
    Construye el contenido de word/document.xml con diseño clínico profesional:
    - Encabezado principal con título y distintivo MIVOR
    - Tabla / bloques de metadatos (Servicio, Especialidad, Paciente, Médico, Fecha)
    - Secciones con barra/borde de color y contenido claro
    """
    body_elements = []

    # Título principal
    body_elements.append(f"""
    <w:p>
      <w:pPr>
        <w:jc w:val="center"/>
        <w:spacing w:before="120" w:after="60"/>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
          <w:b/>
          <w:sz w:val="44"/>
          <w:color w:val="1D4ED8"/>
        </w:rPr>
        <w:t>{_escape(title)}</w:t>
      </w:r>
    </w:p>
    """)

    # Subtítulo / Badge
    if subtitle:
        body_elements.append(f"""
        <w:p>
          <w:pPr>
            <w:jc w:val="center"/>
            <w:spacing w:before="0" w:after="240"/>
          </w:pPr>
          <w:r>
            <w:rPr>
              <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
              <w:b/>
              <w:sz w:val="20"/>
              <w:color w:val="6B7280"/>
            </w:rPr>
            <w:t>{_escape(subtitle)}</w:t>
          </w:r>
        </w:p>
        """)

    # Tabla de Metadatos
    if metadata:
        meta_rows = []
        for label, val in metadata:
            meta_rows.append(f"""
            <w:tr>
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="2800" w:type="dxa"/>
                  <w:shd w:val="clear" w:color="auto" w:fill="F3F4F6"/>
                  <w:tcMar>
                    <w:top w:w="80" w:type="dxa"/>
                    <w:bottom w:w="80" w:type="dxa"/>
                    <w:left w:w="140" w:type="dxa"/>
                    <w:right w:w="140" w:type="dxa"/>
                  </w:tcMar>
                </w:tcPr>
                <w:p>
                  <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
                  <w:r>
                    <w:rPr>
                      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                      <w:b/>
                      <w:sz w:val="20"/>
                      <w:color w:val="374151"/>
                    </w:rPr>
                    <w:t>{_escape(label)}</w:t>
                  </w:r>
                </w:p>
              </w:tc>
              <w:tc>
                <w:tcPr>
                  <w:tcW w:w="6200" w:type="dxa"/>
                  <w:shd w:val="clear" w:color="auto" w:fill="FFFFFF"/>
                  <w:tcMar>
                    <w:top w:w="80" w:type="dxa"/>
                    <w:bottom w:w="80" w:type="dxa"/>
                    <w:left w:w="140" w:type="dxa"/>
                    <w:right w:w="140" w:type="dxa"/>
                  </w:tcMar>
                </w:tcPr>
                <w:p>
                  <w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>
                  <w:r>
                    <w:rPr>
                      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                      <w:sz w:val="20"/>
                      <w:color w:val="1F2937"/>
                    </w:rPr>
                    <w:t>{_escape(val)}</w:t>
                  </w:r>
                </w:p>
              </w:tc>
            </w:tr>
            """)

        body_elements.append(f"""
        <w:tbl>
          <w:tblPr>
            <w:tblW w:w="9000" w:type="dxa"/>
            <w:jc w:val="center"/>
            <w:tblBorders>
              <w:top w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>
              <w:left w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>
              <w:bottom w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>
              <w:right w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>
              <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>
              <w:insideV w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>
            </w:tblBorders>
          </w:tblPr>
          {"".join(meta_rows)}
        </w:tbl>
        <w:p><w:pPr><w:spacing w:before="180" w:after="120"/></w:pPr></w:p>
        """)

    # Secciones clínicas o contenido
    for sec_title, sec_content, color in sections:
        clean_color = color.replace("#", "")
        # Título de sección con distintivo
        body_elements.append(f"""
        <w:p>
          <w:pPr>
            <w:pBdr>
              <w:bottom w:val="single" w:sz="12" w:space="4" w:color="{clean_color}"/>
            </w:pBdr>
            <w:spacing w:before="240" w:after="100"/>
          </w:pPr>
          <w:r>
            <w:rPr>
              <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
              <w:b/>
              <w:sz w:val="26"/>
              <w:color w:val="{clean_color}"/>
            </w:rPr>
            <w:t>{_escape(sec_title)}</w:t>
          </w:r>
        </w:p>
        """)

        # Párrafos de contenido
        lines = (sec_content or "No especificado.").split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                body_elements.append("""<w:p><w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr></w:p>""")
                continue
            body_elements.append(f"""
            <w:p>
              <w:pPr>
                <w:spacing w:before="40" w:after="60" w:line="276" w:lineRule="auto"/>
                <w:ind w:left="140"/>
              </w:pPr>
              <w:r>
                <w:rPr>
                  <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
                  <w:sz w:val="22"/>
                  <w:color w:val="334155"/>
                </w:rPr>
                <w:t xml:space="preserve">{_escape(line_str)}</w:t>
              </w:r>
            </w:p>
            """)

    # Pie de página / notas
    body_elements.append("""
    <w:p>
      <w:pPr>
        <w:jc w:val="center"/>
        <w:spacing w:before="360" w:after="60"/>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
          <w:i/>
          <w:sz w:val="18"/>
          <w:color w:val="9CA3AF"/>
        </w:rPr>
        <w:t>Mivor · Salud Digital · Documento Clínico Confidencial</w:t>
      </w:r>
    </w:p>
    """)

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {"".join(body_elements)}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def _package_docx(document_xml: str) -> bytes:
    """Empaqueta los archivos OpenXML en un contenedor ZIP para formar un archivo .docx válido."""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:eastAsia="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
        <w:sz w:val="22"/>
        <w:szCs w:val="22"/>
        <w:lang w:val="es-ES"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:after="160" w:line="276" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
</w:styles>"""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/document.xml", document_xml)

    return buf.getvalue()


def create_clinical_report_docx(
    service_type: str,
    specialty: str = "Medicina General",
    date_str: str | None = None,
    patient_name: str | None = None,
    patient_gender: str | None = None,
    doctor_name: str | None = None,
    summary: str = "",
) -> bytes:
    """Genera el INFORME MÉDICO oficial en formato Microsoft Word (.docx)."""
    date_label = date_str or datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    sections_map = _parse_clinical_sections(summary)

    metadata = [
        ("Servicio:", (service_type or "Videollamada").strip()),
        ("Especialidad:", (specialty or "Medicina General").strip()),
        ("Fecha:", date_label),
        ("Médico tratante:", (doctor_name or "Médico").strip()),
        ("Paciente:", (patient_name or "No especificado").strip()),
        ("Sexo del paciente:", (patient_gender or "No especificado").strip()),
    ]

    clinical_sections = [
        ("MOTIVO DE CONSULTA", sections_map.get("motivo", "No referido durante la consulta."), "2563EB"),
        ("EXPLORACIÓN FÍSICA", sections_map.get("exploracion", "No referida o no evaluada en esta sesión."), "059669"),
        ("IMPRESIÓN DIAGNÓSTICA", sections_map.get("diagnostico", "No especificada."), "7C3AED"),
        ("PLAN Y TRATAMIENTO", sections_map.get("plan", "No especificado."), "D97706"),
    ]

    doc_xml = _build_docx_xml(
        title="INFORME MÉDICO",
        subtitle="MIVOR · SALUD DIGITAL — HISTORIAL CLÍNICO",
        metadata=metadata,
        sections=clinical_sections,
    )
    return _package_docx(doc_xml)


def create_transcription_docx(
    service_type: str,
    specialty: str = "Medicina General",
    date_str: str | None = None,
    patient_name: str | None = None,
    doctor_name: str | None = None,
    transcript: str = "",
) -> bytes:
    """Genera la TRANSCRIPCIÓN COMPLETA de la consulta en formato Word (.docx)."""
    date_label = date_str or datetime.utcnow().strftime("%d/%m/%Y %H:%M")

    metadata = [
        ("Servicio:", (service_type or "Videollamada").strip()),
        ("Especialidad:", (specialty or "Medicina General").strip()),
        ("Fecha:", date_label),
        ("Médico tratante:", (doctor_name or "Médico").strip()),
        ("Paciente:", (patient_name or "No especificado").strip()),
    ]

    sections = [
        ("TRANSCRIPCIÓN COMPLETA DEL AUDIO", transcript or "No hay transcripción disponible.", "6D28D9"),
    ]

    doc_xml = _build_docx_xml(
        title="TRANSCRIPCIÓN DE CONSULTA",
        subtitle="MIVOR · SALUD DIGITAL — REGISTRO DE AUDIO",
        metadata=metadata,
        sections=sections,
    )
    return _package_docx(doc_xml)


def create_combined_report_docx(
    service_type: str,
    specialty: str = "Medicina General",
    date_str: str | None = None,
    patient_name: str | None = None,
    patient_gender: str | None = None,
    doctor_name: str | None = None,
    summary: str = "",
    transcript: str = "",
) -> bytes:
    """Genera el documento integral con INFORME MÉDICO y TRANSCRIPCIÓN en Word (.docx)."""
    date_label = date_str or datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    sections_map = _parse_clinical_sections(summary)

    metadata = [
        ("Servicio:", (service_type or "Videollamada").strip()),
        ("Especialidad:", (specialty or "Medicina General").strip()),
        ("Fecha:", date_label),
        ("Médico tratante:", (doctor_name or "Médico").strip()),
        ("Paciente:", (patient_name or "No especificado").strip()),
        ("Sexo del paciente:", (patient_gender or "No especificado").strip()),
    ]

    sections = [
        ("MOTIVO DE CONSULTA", sections_map.get("motivo", "No referido durante la consulta."), "2563EB"),
        ("EXPLORACIÓN FÍSICA", sections_map.get("exploracion", "No referida o no evaluada en esta sesión."), "059669"),
        ("IMPRESIÓN DIAGNÓSTICA", sections_map.get("diagnostico", "No especificada."), "7C3AED"),
        ("PLAN Y TRATAMIENTO", sections_map.get("plan", "No especificado."), "D97706"),
        ("TRANSCRIPCIÓN COMPLETA DE AUDIO", transcript or "No hay transcripción disponible.", "6D28D9"),
    ]

    doc_xml = _build_docx_xml(
        title="INFORME MÉDICO Y TRANSCRIPCIÓN",
        subtitle="MIVOR · SALUD DIGITAL — EXPEDIENTE INTEGRAL",
        metadata=metadata,
        sections=sections,
    )
    return _package_docx(doc_xml)


def extract_text_and_sections_from_docx(file_bytes: bytes) -> dict:
    """
    Lee un archivo Word (.docx) o texto plano (.txt) subido por el médico:
    - Extrae el texto completo de los párrafos.
    - Identifica si contiene las 4 secciones clínicas estándar:
      (Motivo de consulta, Exploración física, Impresión diagnóstica, Plan y tratamiento).
    - Identifica si contiene sección de Transcripción.
    - Retorna el resumen normalizado, las 4 secciones desglosadas y la transcripción.
    """
    full_text = ""
    is_docx = False

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            if "word/document.xml" in z.namelist():
                xml_data = z.read("word/document.xml")
                root = ET.fromstring(xml_data)
                w_namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                
                paragraphs = []
                for p in root.iter(f"{{{w_namespace}}}p"):
                    texts = [
                        node.text for node in p.iter(f"{{{w_namespace}}}t") if node.text
                    ]
                    p_text = "".join(texts).strip()
                    if p_text:
                        paragraphs.append(p_text)
                full_text = "\n\n".join(paragraphs)
                is_docx = True
    except Exception:
        # Si no es un docx válido, intentar leerlo como texto plano utf-8 o latin-1
        try:
            full_text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                full_text = file_bytes.decode("latin-1")
            except Exception:
                full_text = ""

    if not full_text.strip():
        raise ValueError("El archivo subido está vacío o no se pudo interpretar como Word (.docx) o texto.")

    # Verificar si el documento contiene un bloque específico para transcripción
    transcript_text = ""
    transcript_split = re.split(
        r"(?:---|===)?\s*(?:transcripci[oó]n(?:\s+completa)?(?:\s+del\s+audio)?)\s*(?:---|===)?",
        full_text,
        flags=re.IGNORECASE,
    )
    if len(transcript_split) > 1:
        clinical_portion = transcript_split[0].strip()
        transcript_text = "\n\n".join(transcript_split[1:]).strip()
    else:
        clinical_portion = full_text.strip()

    sections = _parse_clinical_sections(clinical_portion)

    # Reconstruir un summary_text estandarizado con los 4 encabezados
    summary_text = (
        f"MOTIVO DE CONSULTA:\n{sections.get('motivo', 'No referido.')}\n\n"
        f"EXPLORACIÓN FÍSICA:\n{sections.get('exploracion', 'No referida.')}\n\n"
        f"IMPRESIÓN DIAGNÓSTICA:\n{sections.get('diagnostico', 'No especificada.')}\n\n"
        f"PLAN Y TRATAMIENTO:\n{sections.get('plan', 'No especificado.')}"
    )

    return {
        "is_docx": is_docx,
        "full_text": full_text,
        "summary_text": summary_text,
        "sections": sections,
        "transcript_text": transcript_text,
    }
