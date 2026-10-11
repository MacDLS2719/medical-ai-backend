import textwrap
import unicodedata


def create_transcription_report_pdf(summary: str, transcript: str) -> bytes:
    lines = [
        ("bold", "INFORME DE TRANSCRIPCIÓN"),
        ("regular", ""),
        ("bold", "RESUMEN DE IA"),
        *[("regular", line) for line in _wrap_text(summary)],
        ("regular", ""),
        ("bold", "TRANSCRIPCIÓN COMPLETA"),
        *[("regular", line) for line in _wrap_text(transcript)],
    ]
    page_lines = [lines[index:index + 48] for index in range(0, len(lines), 48)]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]

    page_object_ids = []
    for page in page_lines:
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_object_ids.append(page_id)
        stream = _render_page(page)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
            + stream
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


def _wrap_text(text: str) -> list[str]:
    paragraphs = text.splitlines() or [""]
    lines = []
    for paragraph in paragraphs:
        wrapped = textwrap.wrap(paragraph, width=88, replace_whitespace=True) or [""]
        lines.extend(wrapped)
    return lines


def _render_page(lines: list[tuple[str, str]]) -> bytes:
    title = _pdf_text("INFORME DE TRANSCRIPCIÓN")
    commands = ["BT", "/F2 16 Tf", "50 750 Td", f"({title}) Tj"]
    y = 720
    for style, text in lines:
        if text == "INFORME DE TRANSCRIPCIÓN":
            continue
        font = "F2" if style == "bold" else "F1"
        size = 12 if style == "bold" else 10
        escaped = _pdf_text(text)
        commands.extend(
            [
                f"/{font} {size} Tf",
                f"1 0 0 1 50 {y} Tm",
                f"({escaped}) Tj",
            ]
        )
        y -= 14
    commands.append("ET")
    return "\n".join(commands).encode("latin-1")


def _pdf_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    encoded = normalized.encode("cp1252", errors="replace")
    text = encoded.decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
