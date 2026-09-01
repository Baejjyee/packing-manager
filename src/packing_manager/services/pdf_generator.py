"""ReportLab generators for Packing List and two-up Packing Labels."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from packing_manager.config import FONT_DIR
from packing_manager.models import PackingDocument, PackingLine, PackingPackage


_FONT_NAME = "PackingManagerFont"
_PACKING_LIST_ROWS_PER_PAGE = 10


class PackingPdfGenerator:
    """Generate Packing List and A4 left/right two-up Packing Labels."""

    def __init__(self) -> None:
        _register_korean_font()

    def create_packing_list(
        self, document: PackingDocument, output_path: Path
    ) -> None:
        """Create an A4 landscape Packing List PDF."""
        document.validate()
        path = _prepare_output_path(output_path)
        pdf = Canvas(str(path), pagesize=landscape(A4))
        page_width, page_height = landscape(A4)

        indexed_lines = _indexed_lines(document.lines)
        pages = [
            indexed_lines[index : index + _PACKING_LIST_ROWS_PER_PAGE]
            for index in range(0, len(indexed_lines), _PACKING_LIST_ROWS_PER_PAGE)
        ]
        for page_number, page_lines in enumerate(pages, 1):
            self._draw_packing_list_page(
                pdf,
                document,
                page_lines,
                page_width,
                page_height,
                page_number,
                len(pages),
            )
            pdf.showPage()
        pdf.save()

    def create_packing_labels(
        self, document: PackingDocument, output_path: Path
    ) -> None:
        """Create an A4 landscape PDF with two labels per page."""
        document.validate()
        path = _prepare_output_path(output_path)
        pdf = Canvas(str(path), pagesize=landscape(A4))
        page_width, page_height = landscape(A4)
        pages = _label_pages(document.lines)

        for page_entries in pages:
            entries = [entry for entry in page_entries if entry is not None]
            for column, (package_number, line, package) in enumerate(entries):
                self._draw_label(
                    pdf,
                    document,
                    package_number,
                    line,
                    package,
                    column * page_width / 2,
                    page_width / 2,
                    page_height,
                )
            if page_entries[1] is not None:
                pdf.setStrokeColor(colors.HexColor("#b7b7b7"))
                pdf.setLineWidth(0.4)
                pdf.setDash(2, 2)
                pdf.line(page_width / 2, 8 * mm, page_width / 2, page_height - 8 * mm)
                pdf.setDash()
            pdf.showPage()
        pdf.save()

    def _draw_packing_list_page(
        self,
        pdf: Canvas,
        document: PackingDocument,
        page_lines: list[tuple[int, int, PackingLine]],
        page_width: float,
        page_height: float,
        page_number: int,
        page_count: int,
    ) -> None:
        pdf.setFillColor(colors.black)
        pdf.setFont(_FONT_NAME, 20)
        pdf.drawCentredString(
            page_width / 2,
            page_height - 24 * mm,
            f"{document.company_name} PACKING LIST",
        )
        pdf.setFont(_FONT_NAME, 11)
        pdf.drawString(18 * mm, page_height - 38 * mm, document.supplier)
        shipping = document.shipping_date.strftime("%Y. %m. %d.")
        pdf.drawRightString(
            page_width - 18 * mm, page_height - 38 * mm, f"선적일 : {shipping}"
        )

        units = {line.unit for line in document.lines if line.unit}
        quantity_header = (
            f"발주량({next(iter(units))})" if len(units) == 1 else "발주량"
        )
        headers = (
            "NO.",
            "품 명",
            "규격",
            "색 상",
            quantity_header,
            "중량(KG)",
            "C.B.M",
            "PACKING 내역",
            "R/L 수",
            "ITEM",
            "발주 NO.",
        )
        rows: list[list[object]] = [list(headers)]
        for start, end, line in page_lines:
            rows.append(
                [
                    _package_range(start, end),
                    _paragraph(line.english_name, 8),
                    line.specification,
                    _paragraph(line.color, 8),
                    _quantity_with_loss(line.order_quantity, line.loss),
                    _format_number(line.weight_kg, 1),
                    _format_number(line.cbm, 2),
                    _package_summary(line.packages),
                    str(len(line.packages)),
                    "",
                    "",
                ]
            )

        visible_rows = max(_PACKING_LIST_ROWS_PER_PAGE, len(page_lines))
        rows.extend([[""] * len(headers) for _ in range(visible_rows - len(page_lines))])
        if visible_rows:
            rows[1][9] = _paragraph(document.item_name, 9)
            rows[1][10] = _paragraph(
                f"{document.po_number}\n"
                f"({_format_number(document.finished_goods_quantity)} PRS)",
                9,
            )

        total_quantity = sum((line.total_quantity for line in document.lines), Decimal())
        total_weight = sum((line.weight_kg for line in document.lines), Decimal())
        total_cbm = sum((line.cbm for line in document.lines), Decimal())
        total_packages = sum(len(line.packages) for line in document.lines)
        rows.append(
            [
                "TOTAL",
                "",
                "",
                "",
                _format_number(total_quantity),
                _format_number(total_weight, 1),
                _format_number(total_cbm, 2),
                "",
                str(total_packages),
                "",
                "",
            ]
        )

        column_widths = [
            15 * mm,
            45 * mm,
            16 * mm,
            26 * mm,
            23 * mm,
            20 * mm,
            18 * mm,
            41 * mm,
            16 * mm,
            31 * mm,
            31 * mm,
        ]
        row_heights = [9 * mm] + [12 * mm] * visible_rows + [9 * mm]
        table = Table(rows, colWidths=column_widths, rowHeights=row_heights)
        last_body_row = visible_rows
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                    ("GRID", (0, 0), (-1, -1), 0.65, colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("SPAN", (9, 1), (9, last_body_row)),
                    ("SPAN", (10, 1), (10, last_body_row)),
                    ("SPAN", (0, -1), (3, -1)),
                    ("ALIGN", (0, -1), (0, -1), "LEFT"),
                    ("LEFTPADDING", (0, -1), (0, -1), 4 * mm),
                ]
            )
        )
        table_width, _ = table.wrap(0, 0)
        table.drawOn(pdf, (page_width - table_width) / 2, 18 * mm)

        if page_count > 1:
            pdf.setFont(_FONT_NAME, 8)
            pdf.drawRightString(
                page_width - 18 * mm, 10 * mm, f"{page_number} / {page_count}"
            )

    def _draw_label(
        self,
        pdf: Canvas,
        document: PackingDocument,
        package_number: int,
        line: PackingLine,
        _package: PackingPackage,
        left: float,
        width: float,
        height: float,
    ) -> None:
        margin = 8 * mm
        content_left = left + margin
        content_right = left + width - margin
        value_x = left + 54 * mm
        top = height - 18 * mm

        diamond_center_x = left + 25 * mm
        diamond_center_y = top - 10 * mm
        diamond_width = 29 * mm
        diamond_height = 19 * mm
        path = pdf.beginPath()
        path.moveTo(diamond_center_x, diamond_center_y + diamond_height / 2)
        path.lineTo(diamond_center_x + diamond_width / 2, diamond_center_y)
        path.lineTo(diamond_center_x, diamond_center_y - diamond_height / 2)
        path.lineTo(diamond_center_x - diamond_width / 2, diamond_center_y)
        path.close()
        pdf.setLineWidth(1)
        pdf.drawPath(path)
        pdf.setFont(_FONT_NAME, 20)
        pdf.drawCentredString(diamond_center_x, diamond_center_y - 3 * mm, "S.D")

        pdf.setFont(_FONT_NAME, 12)
        pdf.drawString(left + 50 * mm, top - 5 * mm, "선적 LIST No:")
        _draw_fitted(
            pdf,
            document.packing_list_number,
            left + 85 * mm,
            top - 5 * mm,
            content_right - (left + 85 * mm),
            11,
        )
        _draw_rule(pdf, left + 50 * mm, content_right, top - 15 * mm)

        rows = [
            ("P/G NO :", str(package_number)),
            ("BUYER :", document.buyer),
            ("PO NO :", document.po_number),
            ("ITEM :", document.item_name),
            ("Q'TY :", f"{_format_number(document.finished_goods_quantity)} PRS"),
            ("MATERIAL :", line.english_name),
            ("COLOR :", line.color),
            ("SHIP DATE", document.shipping_date.strftime("%Y. %m. %d.")),
        ]
        start_y = top - 34 * mm
        spacing = 15 * mm
        for row_index, (label, value) in enumerate(rows):
            y = start_y - row_index * spacing
            pdf.setFont(_FONT_NAME, 12)
            pdf.drawString(content_left, y, label)
            _draw_fitted(pdf, value, value_x, y, content_right - value_x, 14)
            _draw_rule(pdf, content_left, content_right, y - 3 * mm)

        pdf.setFont(_FONT_NAME, 14)
        pdf.drawCentredString(left + width / 2, 15 * mm, document.origin)


def _register_korean_font() -> None:
    if _FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return
    candidates = (
        FONT_DIR / "NotoSansKR.ttf",
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/gulim.ttc"),
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    )
    font_path = next((path for path in candidates if path.is_file()), None)
    if font_path is None:
        raise RuntimeError("한글 PDF 생성에 사용할 글꼴을 찾지 못했습니다.")
    pdfmetrics.registerFont(TTFont(_FONT_NAME, str(font_path)))


def _prepare_output_path(output_path: Path) -> Path:
    path = Path(output_path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("출력 파일 확장자는 .pdf여야 합니다.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _indexed_lines(lines: list[PackingLine]) -> list[tuple[int, int, PackingLine]]:
    result: list[tuple[int, int, PackingLine]] = []
    start = 1
    for line in lines:
        end = start + len(line.packages) - 1
        result.append((start, end, line))
        start = end + 1
    return result


def _flatten_packages(
    lines: list[PackingLine],
) -> list[tuple[int, PackingLine, PackingPackage]]:
    result: list[tuple[int, PackingLine, PackingPackage]] = []
    number = 1
    for line in lines:
        for package in line.packages:
            result.append((number, line, package))
            number += 1
    return result


def _label_pages(
    lines: list[PackingLine],
) -> list[
    tuple[
        tuple[int, PackingLine, PackingPackage],
        tuple[int, PackingLine, PackingPackage] | None,
    ]
]:
    """Pair sequential labels left/right, leaving the final right side blank."""
    packages = _flatten_packages(lines)
    return [
        (
            packages[index],
            packages[index + 1] if index + 1 < len(packages) else None,
        )
        for index in range(0, len(packages), 2)
    ]


def _package_range(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}~{end}"


def _package_summary(packages: list[PackingPackage]) -> str:
    totals = [_format_number(package.total_quantity) for package in packages]
    counts = Counter(totals)
    return "  ".join(f"{quantity}*{count}" for quantity, count in counts.items())


def _quantity_with_loss(quantity: Decimal, loss: Decimal) -> str:
    value = _format_number(quantity)
    return f"{value}+{_format_number(loss)}" if loss else value


def _format_number(value: Decimal, places: int | None = None) -> str:
    if places is not None:
        return f"{value:,.{places}f}"
    if value == value.to_integral_value():
        return f"{int(value):,}"
    return format(value, "f")


def _paragraph(value: str, font_size: int) -> Paragraph:
    style = ParagraphStyle(
        "packing-cell",
        fontName=_FONT_NAME,
        fontSize=font_size,
        leading=font_size + 2,
        alignment=TA_CENTER,
    )
    return Paragraph(escape(value).replace("\n", "<br/>"), style)


def _draw_rule(pdf: Canvas, left: float, right: float, y: float) -> None:
    pdf.saveState()
    pdf.setStrokeColor(colors.HexColor("#777777"))
    pdf.setLineWidth(0.4)
    pdf.setDash(1, 1)
    pdf.line(left, y, right, y)
    pdf.restoreState()


def _draw_fitted(
    pdf: Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    preferred_size: float,
) -> None:
    size = preferred_size
    while size > 7 and pdfmetrics.stringWidth(text, _FONT_NAME, size) > max_width:
        size -= 0.5
    pdf.setFont(_FONT_NAME, size)
    pdf.drawCentredString(x + max_width / 2, y, text)
