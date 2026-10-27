# backend/app/services/invoice_pdf_service.py
"""
Servicio generador de facturas oficiales médicas en formato PDF (PDF 1.4 binario estándar).
Soporta tanto facturas de Ingresos (honorarios médicos, consultas)
como facturas de Gastos (proveedores, suministros, servicios).
"""

import textwrap
import unicodedata
from datetime import datetime
from typing import Any


def _pdf_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", str(value or ""))
    normalized = normalized.replace("€", "EUR").replace("â‚¬", "EUR")
    encoded = normalized.encode("cp1252", errors="replace")
    text = encoded.decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _format_money(amount: float, currency: str = "EUR") -> str:
    curr = (currency or "EUR").upper()
    val_str = f"{float(amount or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if curr == "USD":
        return f"$ {val_str}"
    return f"{val_str} EUR"


class _InvoicePDFBuilder:
    PAGE_WIDTH = 612   # Standard Letter / A4-compatible
    PAGE_HEIGHT = 792
    LEFT_MARGIN = 40
    RIGHT_MARGIN = 40
    CONTENT_WIDTH = 532  # 612 - 40 - 40
    TOP_MARGIN = 752
    BOTTOM_MARGIN = 50

    def __init__(self):
        self.pages: list[list[str]] = [[]]
        self.current_y = self.TOP_MARGIN

    @property
    def current_page_commands(self) -> list[str]:
        return self.pages[-1]

    def new_page(self, title: str = "FACTURA MÉDICA"):
        self.pages.append([])
        self.current_y = self.TOP_MARGIN
        cmds = self.current_page_commands
        cmds.extend([
            "q",
            "0.50 0.55 0.65 rg",
            "BT",
            "/F1 8 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} 758 Tm",
            f"({_pdf_text(title + ' - Continuación')}) Tj",
            "ET",
            "0.88 0.90 0.94 RG",
            "0.5 w",
            f"{self.LEFT_MARGIN} 750 m {self.LEFT_MARGIN + self.CONTENT_WIDTH} 750 l S",
            "Q",
        ])
        self.current_y = 730

    def ensure_space(self, height: float, title: str = "FACTURA MÉDICA"):
        if self.current_y - height < self.BOTTOM_MARGIN:
            self.new_page(title)

    def add_spacing(self, pts: float):
        self.current_y -= pts

    def draw_top_accent_bar(self, is_expense: bool = False):
        cmds = self.current_page_commands
        # Blue (income) or Rose/Indigo (expense)
        r, g, b = (0.85, 0.20, 0.35) if is_expense else (0.12, 0.44, 0.88)
        cmds.extend([
            "q",
            f"{r:.3f} {g:.3f} {b:.3f} rg",
            f"{self.LEFT_MARGIN} {self.current_y} {self.CONTENT_WIDTH} 5 re f",
            "Q",
        ])
        self.current_y -= 22

    def draw_header(
        self,
        invoice_number: str,
        invoice_type: str,
        issue_date: str,
        due_date: str | None,
        payment_status: str,
    ):
        cmds = self.current_page_commands
        is_expense = invoice_type == "expense"
        r, g, b = (0.85, 0.20, 0.35) if is_expense else (0.12, 0.44, 0.88)
        type_title = "FACTURA DE COMPRA / GASTO" if is_expense else "FACTURA DE INGRESO"
        status_label = "PAGADA" if payment_status.upper() in ("PAID", "PAGADA", "COMPLETED") else "PENDIENTE"

        # Badge y Título Izquierda
        cmds.extend([
            "q",
            "BT",
            f"{r:.3f} {g:.3f} {b:.3f} rg",
            "/F2 9 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} {self.current_y} Tm",
            f"({_pdf_text('MIVOR SALUD DIGITAL · SISTEMA DE FACTURACIÓN')}) Tj",
            "ET",
            "BT",
            "0.09 0.12 0.18 rg",
            "/F2 18 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} {self.current_y - 20} Tm",
            f"({_pdf_text(type_title)}) Tj",
            "ET",
            "Q",
        ])

        # Recuadro Código de Factura a la Derecha
        box_w = 175
        box_h = 44
        box_x = self.LEFT_MARGIN + self.CONTENT_WIDTH - box_w
        box_y = self.current_y - 26

        cmds.extend([
            "q",
            "0.96 0.97 1.00 rg" if not is_expense else "1.00 0.96 0.97 rg",
            f"{r:.3f} {g:.3f} {b:.3f} RG",
            "1 w",
            f"{box_x} {box_y} {box_w} {box_h} re B",
            "BT",
            "0.40 0.45 0.55 rg",
            "/F2 8 Tf",
            f"1 0 0 1 {box_x + 10} {box_y + 28} Tm",
            f"({_pdf_text('Nº DE FACTURA')}) Tj",
            "ET",
            "BT",
            f"{r:.3f} {g:.3f} {b:.3f} rg",
            "/F2 13 Tf",
            f"1 0 0 1 {box_x + 10} {box_y + 11} Tm",
            f"({_pdf_text(invoice_number)}) Tj",
            "ET",
            "Q",
        ])

        self.current_y -= 44

        # Fila de metadatos (Fecha Emisión, Vencimiento, Estado)
        cmds.extend([
            "q",
            "BT",
            "0.45 0.50 0.60 rg",
            "/F1 9 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} {self.current_y} Tm",
            f"({_pdf_text(f'Fecha de emisión: {issue_date}')}) Tj",
            f"1 0 0 1 {self.LEFT_MARGIN + 160} {self.current_y} Tm",
            f"({_pdf_text(f'Vencimiento: {due_date or issue_date}')}) Tj",
            f"1 0 0 1 {self.LEFT_MARGIN + 320} {self.current_y} Tm",
            f"({_pdf_text('Estado:')}) Tj",
            "ET",
            "BT",
            "0.10 0.60 0.30 rg" if status_label == "PAGADA" else "0.85 0.50 0.10 rg",
            "/F2 9 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN + 360} {self.current_y} Tm",
            f"({_pdf_text(status_label)}) Tj",
            "ET",
            "Q",
        ])

        self.current_y -= 18

    def draw_parties_cards(
        self,
        issuer: dict[str, Any],
        recipient: dict[str, Any],
        is_expense: bool = False,
    ):
        card_w = (self.CONTENT_WIDTH - 14) / 2
        card_h = 88
        card_y = self.current_y - card_h

        # Card 1: Emisor (Doctor / Clínica para ingresos, Proveedor para gastos)
        issuer_title = "PROVEEDOR / EMISOR" if is_expense else "EMISOR (PROFESIONAL MÉDICO)"
        recip_title = "CLIENTE (MÉDICO / CLÍNICA)" if is_expense else "DATOS DEL RECEPTOR (PACIENTE / CLIENTE)"

        for i, (title, data) in enumerate([(issuer_title, issuer), (recip_title, recipient)]):
            cx = self.LEFT_MARGIN if i == 0 else (self.LEFT_MARGIN + card_w + 14)
            cmds = self.current_page_commands
            cmds.extend([
                "q",
                "0.98 0.98 0.99 rg",
                "0.88 0.90 0.94 RG",
                "0.8 w",
                f"{cx} {card_y} {card_w} {card_h} re B",
                "BT",
                "0.15 0.22 0.35 rg",
                "/F2 9 Tf",
                f"1 0 0 1 {cx + 10} {card_y + card_h - 15} Tm",
                f"({_pdf_text(title)}) Tj",
                "ET",
                "BT",
                "0.10 0.12 0.18 rg",
                "/F2 10 Tf",
                f"1 0 0 1 {cx + 10} {card_y + card_h - 30} Tm",
                f"({_pdf_text(data.get('name') or 'No especificado')}) Tj",
                "ET",
                "BT",
                "0.35 0.40 0.50 rg",
                "/F1 8.5 Tf",
                f"1 0 0 1 {cx + 10} {card_y + card_h - 44} Tm",
                f"({_pdf_text(('NIF/CIF: ' + str(data.get('nif') or data.get('tax_id'))) if (data.get('nif') or data.get('tax_id')) else ('Email: ' + str(data.get('email') or 'doctor@mivor.com')))}) Tj",
                f"1 0 0 1 {cx + 10} {card_y + card_h - 57} Tm",
                f"({_pdf_text('Dirección: ' + str(data.get('address') or 'Consultorio Médico Mivor'))}) Tj",
                f"1 0 0 1 {cx + 10} {card_y + card_h - 70} Tm",
                f"({_pdf_text(('Contacto: ' + str(data.get('email') or data.get('phone') or '')) if (data.get('nif') or data.get('tax_id')) else ('Tel: ' + str(data.get('phone') or 'Consultorio Privado')))}) Tj",
                "ET",
                "Q",
            ])

        self.current_y = card_y - 18

    def draw_items_table(self, items: list[dict[str, Any]], currency: str = "EUR"):
        col_desc_w = 260
        col_qty_w = 60
        col_price_w = 100
        col_total_w = self.CONTENT_WIDTH - col_desc_w - col_qty_w - col_price_w

        cmds = self.current_page_commands

        # Encabezado tabla
        th_h = 22
        th_y = self.current_y - th_h
        cmds.extend([
            "q",
            "0.12 0.18 0.28 rg",
            f"{self.LEFT_MARGIN} {th_y} {self.CONTENT_WIDTH} {th_h} re f",
            "BT",
            "1.0 1.0 1.0 rg",
            "/F2 8.5 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN + 10} {th_y + 7} Tm",
            f"({_pdf_text('DESCRIPCIÓN / CONCEPTO')}) Tj",
            f"1 0 0 1 {self.LEFT_MARGIN + col_desc_w + 10} {th_y + 7} Tm",
            f"({_pdf_text('CANT.')}) Tj",
            f"1 0 0 1 {self.LEFT_MARGIN + col_desc_w + col_qty_w + 10} {th_y + 7} Tm",
            f"({_pdf_text('PRECIO UNIT.')}) Tj",
            f"1 0 0 1 {self.LEFT_MARGIN + col_desc_w + col_qty_w + col_price_w + 10} {th_y + 7} Tm",
            f"({_pdf_text('TOTAL')}) Tj",
            "ET",
            "Q",
        ])
        self.current_y = th_y

        # Filas de items
        for idx, item in enumerate(items):
            desc = str(item.get("description") or item.get("concept") or "Servicio médico profesional")
            qty = float(item.get("quantity") or 1)
            price = float(item.get("unit_price") or item.get("amount") or 0)
            total = float(item.get("amount") or (qty * price))

            row_h = 24
            row_y = self.current_y - row_h
            bg_cmd = "0.98 0.98 0.99 rg" if idx % 2 == 1 else "1.0 1.0 1.0 rg"

            cmds.extend([
                "q",
                bg_cmd,
                f"{self.LEFT_MARGIN} {row_y} {self.CONTENT_WIDTH} {row_h} re f",
                "0.90 0.92 0.95 RG",
                "0.5 w",
                f"{self.LEFT_MARGIN} {row_y} m {self.LEFT_MARGIN + self.CONTENT_WIDTH} {row_y} l S",
                "BT",
                "0.15 0.18 0.25 rg",
                "/F1 9 Tf",
                f"1 0 0 1 {self.LEFT_MARGIN + 10} {row_y + 7} Tm",
                f"({_pdf_text(desc[:46])}) Tj",
                f"1 0 0 1 {self.LEFT_MARGIN + col_desc_w + 18} {row_y + 7} Tm",
                f"({_pdf_text(str(int(qty) if qty.is_integer() else qty))}) Tj",
                f"1 0 0 1 {self.LEFT_MARGIN + col_desc_w + col_qty_w + 10} {row_y + 7} Tm",
                f"({_pdf_text(_format_money(price, currency))}) Tj",
                "/F2 9 Tf",
                f"1 0 0 1 {self.LEFT_MARGIN + col_desc_w + col_qty_w + col_price_w + 10} {row_y + 7} Tm",
                f"({_pdf_text(_format_money(total, currency))}) Tj",
                "ET",
                "Q",
            ])
            self.current_y = row_y

        self.current_y -= 14

    def draw_summary_and_payment(
        self,
        subtotal: float,
        tax_rate: float,
        tax_amount: float,
        retention_rate: float,
        retention_amount: float,
        total_amount: float,
        currency: str = "EUR",
        payment_method: str = "Transferencia bancaria",
        notes: str | None = None,
    ):
        cmds = self.current_page_commands

        # Bloque Izquierdo: Información de Pago y Términos Legales
        left_w = 310
        left_h = 100
        left_y = self.current_y - left_h

        legal_note = notes or (
            "Operación médica sujeta a las normativas tributarias vigentes. "
            "Exención de IVA para servicios médicos según normativa de sanidad."
        )
        legal_lines = textwrap.wrap(legal_note, width=54)[:3]

        pm_label = str(payment_method or "Transferencia Bancaria")
        cmds.extend([
            "q",
            "0.98 0.98 0.99 rg",
            "0.88 0.90 0.94 RG",
            "0.8 w",
            f"{self.LEFT_MARGIN} {left_y} {left_w} {left_h} re B",
            "BT",
            "0.20 0.25 0.35 rg",
            "/F2 8.5 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN + 12} {left_y + left_h - 16} Tm",
            f"({_pdf_text('MÉTODO DE PAGO Y CONDICIONES')}) Tj",
            "ET",
            "BT",
            "0.15 0.18 0.25 rg",
            "/F1 8.5 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN + 12} {left_y + left_h - 32} Tm",
            f"({_pdf_text('Forma de pago: ' + pm_label)}) Tj",
            "ET",
            "BT",
            "0.40 0.45 0.55 rg",
            "/F2 8 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN + 12} {left_y + left_h - 48} Tm",
            f"({_pdf_text('NOTAS LEGALES / OBSERVACIONES:')}) Tj",
            "ET",
        ])

        line_y = left_y + left_h - 62
        for l in legal_lines:
            cmds.extend([
                "BT",
                "0.45 0.50 0.60 rg",
                "/F1 7.5 Tf",
                f"1 0 0 1 {self.LEFT_MARGIN + 12} {line_y} Tm",
                f"({_pdf_text(l)}) Tj",
                "ET",
            ])
            line_y -= 11

        cmds.append("Q")

        # Bloque Derecho: Totales financieros
        tot_w = self.CONTENT_WIDTH - left_w - 14
        tot_x = self.LEFT_MARGIN + left_w + 14
        tot_h = left_h
        tot_y = left_y

        cmds.extend([
            "q",
            "0.97 0.98 1.00 rg",
            "0.85 0.88 0.95 RG",
            "1 w",
            f"{tot_x} {tot_y} {tot_w} {tot_h} re B",
            # Subtotal
            "BT",
            "0.35 0.40 0.50 rg",
            "/F1 8.5 Tf",
            f"1 0 0 1 {tot_x + 12} {tot_y + tot_h - 18} Tm",
            f"({_pdf_text('Base Imponible:')}) Tj",
            f"1 0 0 1 {tot_x + tot_w - 75} {tot_y + tot_h - 18} Tm",
            f"({_pdf_text(_format_money(subtotal, currency))}) Tj",
            "ET",
            # IVA
            "BT",
            "0.35 0.40 0.50 rg",
            "/F1 8.5 Tf",
            f"1 0 0 1 {tot_x + 12} {tot_y + tot_h - 32} Tm",
            f"({_pdf_text(f'IVA ({int(tax_rate)}%):')}) Tj",
            f"1 0 0 1 {tot_x + tot_w - 75} {tot_y + tot_h - 32} Tm",
            f"({_pdf_text(_format_money(tax_amount, currency))}) Tj",
            "ET",
        ])

        if retention_rate > 0:
            cmds.extend([
                "BT",
                "0.35 0.40 0.50 rg",
                "/F1 8.5 Tf",
                f"1 0 0 1 {tot_x + 12} {tot_y + tot_h - 46} Tm",
                f"({_pdf_text(f'Retención IRPF ({int(retention_rate)}%):')}) Tj",
                f"1 0 0 1 {tot_x + tot_w - 75} {tot_y + tot_h - 46} Tm",
                f"({_pdf_text('-' + _format_money(retention_amount, currency))}) Tj",
                "ET",
            ])

        # Divisor
        cmds.extend([
            "0.80 0.84 0.90 RG",
            "0.5 w",
            f"{tot_x + 10} {tot_y + 34} m {tot_x + tot_w - 10} {tot_y + 34} l S",
            # TOTAL
            "BT",
            "0.10 0.15 0.25 rg",
            "/F2 11 Tf",
            f"1 0 0 1 {tot_x + 12} {tot_y + 14} Tm",
            f"({_pdf_text('TOTAL FACTURA:')}) Tj",
            "0.12 0.44 0.88 rg",
            "/F2 13 Tf",
            f"1 0 0 1 {tot_x + tot_w - 95} {tot_y + 14} Tm",
            f"({_pdf_text(_format_money(total_amount, currency))}) Tj",
            "ET",
            "Q",
        ])

        self.current_y = left_y - 20

    def draw_signature_and_verification(self, invoice_number: str, doctor_name: str):
        cmds = self.current_page_commands
        sig_y = self.current_y - 45

        # Security Stamp & QR Simulado
        cmds.extend([
            "q",
            "BT",
            "0.40 0.45 0.55 rg",
            "/F2 8 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} {sig_y + 32} Tm",
            f"({_pdf_text('CÓDIGO DE VERIFICACIÓN ELECTRÓNICA')}) Tj",
            "ET",
            "BT",
            "0.50 0.55 0.65 rg",
            "/F1 7.5 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN} {sig_y + 18} Tm",
            f"({_pdf_text('Doc ID: ' + invoice_number + ' · Emisión electrónica certificada por Mivor Health Cloud')}) Tj",
            f"1 0 0 1 {self.LEFT_MARGIN} {sig_y + 6} Tm",
            f"({_pdf_text('Validez legal como comprobante fiscal y contable.')}) Tj",
            "ET",
            # Firma digital
            "BT",
            "0.30 0.35 0.45 rg",
            "/F2 8.5 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN + self.CONTENT_WIDTH - 180} {sig_y + 18} Tm",
            f"({_pdf_text('Firma y Sello del Emisor')}) Tj",
            "ET",
            "0.70 0.75 0.85 RG",
            "0.6 w",
            f"{self.LEFT_MARGIN + self.CONTENT_WIDTH - 190} {sig_y + 28} m {self.LEFT_MARGIN + self.CONTENT_WIDTH - 10} {sig_y + 28} l S",
            "BT",
            "0.50 0.55 0.65 rg",
            "/F3 8 Tf",
            f"1 0 0 1 {self.LEFT_MARGIN + self.CONTENT_WIDTH - 180} {sig_y + 6} Tm",
            f"({_pdf_text(doctor_name)}) Tj",
            "ET",
            "Q",
        ])

    def build(self, invoice_number: str) -> bytes:
        total_pages = len(self.pages)
        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>",
        ]

        page_object_ids = []
        for page_idx, cmds in enumerate(self.pages, start=1):
            page_id = len(objects) + 1
            content_id = page_id + 1
            page_object_ids.append(page_id)

            footer_cmds = [
                "q",
                "0.88 0.90 0.94 RG",
                "0.5 w",
                f"{self.LEFT_MARGIN} 38 m {self.LEFT_MARGIN + self.CONTENT_WIDTH} 38 l S",
                "BT",
                "/F1 7.5 Tf",
                "0.50 0.55 0.65 rg",
                f"1 0 0 1 {self.LEFT_MARGIN} 26 Tm",
                f"({_pdf_text('Factura ' + invoice_number + ' - Documento oficial Mivor')}) Tj",
                f"1 0 0 1 {self.LEFT_MARGIN + self.CONTENT_WIDTH - 65} 26 Tm",
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


def create_invoice_pdf(data: dict[str, Any]) -> bytes:
    """
    Crea el archivo binario PDF de una factura médica a partir de su diccionario de datos.
    """
    builder = _InvoicePDFBuilder()
    invoice_type = data.get("invoice_type") or "income"
    is_expense = invoice_type == "expense"
    raw_num = str(data.get("invoice_number") or "").strip()
    if not raw_num or len(raw_num) > 22 or " " in raw_num:
        import random
        rnd = random.randint(1000, 9999)
        prefix = "GAS" if is_expense else "FAC"
        invoice_number = f"{prefix}-{datetime.utcnow().year}-{rnd}"
    else:
        invoice_number = raw_num
    issue_date = data.get("issue_date") or datetime.utcnow().strftime("%d/%m/%Y")
    due_date = data.get("due_date") or issue_date
    payment_status = data.get("payment_status") or "PAID"
    currency = data.get("currency") or "EUR"

    # Issuer & Recipient
    issuer = data.get("issuer") or {
        "name": data.get("doctor_name") or ("Proveedor / Acreedor" if is_expense else "Dr. Médico Especialista"),
        "nif": data.get("doctor_nif") or "—",
        "address": data.get("doctor_address") or "Centro Médico Mivor",
        "email": data.get("doctor_email") or "",
    }
    recipient = data.get("recipient") or {
        "name": data.get("client_name") or ("Dr. Médico Especialista" if is_expense else "Paciente Particular"),
        "nif": data.get("client_nif") or "—",
        "address": data.get("client_address") or "",
        "email": data.get("client_email") or "",
    }

    # Items
    items = data.get("items") or [
        {
            "description": data.get("description") or "Consulta médica especializada",
            "quantity": 1,
            "unit_price": float(data.get("subtotal") or data.get("total_amount") or 100),
            "amount": float(data.get("subtotal") or data.get("total_amount") or 100),
        }
    ]

    subtotal = float(data.get("subtotal") or sum(float(i.get("amount", 0)) for i in items))
    tax_rate = float(data.get("tax_rate") or 0)
    tax_amount = float(data.get("tax_amount") or (subtotal * tax_rate / 100))
    retention_rate = float(data.get("retention_rate") or 0)
    retention_amount = float(data.get("retention_amount") or (subtotal * retention_rate / 100))
    total_amount = float(data.get("total_amount") or (subtotal + tax_amount - retention_amount))
    payment_method = data.get("payment_method") or "Transferencia bancaria"
    notes = data.get("notes")

    # Renderizado ordenado
    builder.draw_top_accent_bar(is_expense=is_expense)
    builder.draw_header(
        invoice_number=invoice_number,
        invoice_type=invoice_type,
        issue_date=issue_date,
        due_date=due_date,
        payment_status=payment_status,
    )
    builder.draw_parties_cards(issuer=issuer, recipient=recipient, is_expense=is_expense)
    builder.draw_items_table(items=items, currency=currency)
    builder.draw_summary_and_payment(
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        retention_rate=retention_rate,
        retention_amount=retention_amount,
        total_amount=total_amount,
        currency=currency,
        payment_method=payment_method,
        notes=notes,
    )
    builder.draw_signature_and_verification(
        invoice_number=invoice_number,
        doctor_name=issuer.get("name") or "Dr. Tratante",
    )

    return builder.build(invoice_number=invoice_number)
