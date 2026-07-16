"""JSON record -> PDF. The JSON record in the hash chain is the source of
truth; this PDF is a rendered VIEW of it, never the other way around."""
import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_PASS = colors.HexColor("#1a7f4b")
_CONCERN = colors.HexColor("#b45309")

# Thai display names for ruleset components (technical ids stay English in data)
COMPONENT_TH = {
    "side_panel_left": "ผนังด้านซ้าย",
    "side_panel_right": "ผนังด้านขวา",
    "side_panel": "ผนังข้าง",
    "end_panel": "ผนังท้าย",
    "door": "ประตู",
    "roof": "หลังคา",
    "floor": "พื้น",
    "corner_post": "เสามุม",
    "understructure": "โครงใต้ท้อง",
}

_FONT_DIR = Path(__file__).parent / "fonts"


def _register_thai_fonts() -> tuple[str, str]:
    """Register bundled Thai fonts once; fall back to Helvetica if absent."""
    try:
        if "Thai" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("Thai", str(_FONT_DIR / "thai.ttf")))
            pdfmetrics.registerFont(TTFont("Thai-Bold", str(_FONT_DIR / "thai-bold.ttf")))
        return "Thai", "Thai-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


def component_th(component: str) -> str:
    return COMPONENT_TH.get(component, component)


def render_pdf(record: dict) -> bytes:
    font, font_bold = _register_thai_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title=f"Inspection {record['inspection_id']}",
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("titleTh", parent=styles["Title"], fontName=font_bold)
    normal = ParagraphStyle("normalTh", parent=styles["Normal"], fontName=font, fontSize=10, leading=14)
    small = ParagraphStyle("smallTh", parent=normal, fontSize=8, leading=11, textColor=colors.grey)
    cell = ParagraphStyle("cellTh", parent=normal, fontSize=9, leading=12)

    story = [
        Paragraph("บันทึกการตรวจสภาพตู้คอนเทนเนอร์", title),
        Paragraph(
            f"<b>{record['container_id']}</b> · ทิศทาง: {record['direction']} · "
            f"มาตรฐาน: {record['standard']['name']} {record['standard']['version']} · สถานะ: {record['status']}",
            normal,
        ),
        Paragraph(f"เซ็นรับรองโดย {record.get('signed_by')} เมื่อ {record.get('signed_at')}", normal),
        Paragraph(f"รหัสการตรวจ {record['inspection_id']}", small),
        Spacer(1, 6 * mm),
    ]

    rows = [["ชิ้นส่วน", "สิ่งที่พบ", "ผล", "ค่าที่วัด", "ตัดสินโดย", "หมายเหตุ / หลักฐาน"]]
    row_styles = []
    for i, f in enumerate(record.get("findings", []), start=1):
        m = f.get("measurement")
        measured = (
            f"{m['value_mm']} mm เทียบเกณฑ์ {m['limit_mm']} mm ({m['source']})"
            if m else "— (รอผู้ตรวจตัดสิน)"
        )
        decision = f["decision_source"] + (" · OVERRIDE" if f.get("human_override") else "")
        note = f.get("note") or ""
        evidence = ", ".join(f.get("evidence", []))
        rows.append([
            Paragraph(component_th(f["component"]), cell),
            Paragraph(f["concern"], cell),
            Paragraph(f.get("result") or "", cell),
            Paragraph(measured, cell),
            Paragraph(decision, cell),
            Paragraph(" · ".join(x for x in (note, evidence) if x), cell),
        ])
        row_styles.append((
            "TEXTCOLOR", (2, i), (2, i),
            _PASS if f.get("result") == "pass" else _CONCERN,
        ))

    table = Table(rows, colWidths=[30 * mm, 16 * mm, 16 * mm, 38 * mm, 26 * mm, 48 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        *row_styles,
    ]))
    story += [
        table,
        Spacer(1, 8 * mm),
        Paragraph("ลำดับการตัดสิน: Human &gt; Metrology &gt; Vision — "
                  "Vision ชี้จุดที่ควรตรวจเท่านั้น ไม่ใช่ผู้ตัดสิน บันทึกนี้ผ่านการเซ็นรับรองโดยมนุษย์", small),
        Spacer(1, 4 * mm),
        Paragraph(f"hash chain กันแก้ไขย้อนหลัง — hash: {record.get('hash')}", small),
        Paragraph(f"prev: {record.get('prev_hash')}", small),
        Paragraph("เรนเดอร์จากบันทึก JSON (แหล่งข้อมูลจริง / source of truth)", small),
    ]
    doc.build(story)
    return buf.getvalue()
