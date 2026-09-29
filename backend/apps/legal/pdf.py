"""PDFs locais, sem HTML ativo, URLs externas ou interpretação de código."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

FONT_ROOT = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("Iustus", str(FONT_ROOT / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("IustusBold", str(FONT_ROOT / "VeraBd.ttf")))


def supported(text):
    widths = pdfmetrics.getFont("Iustus").face.charWidths
    return all(char in "\n\r\t" or ord(char) in widths for char in text)


def mandate_pdf(body, *, template_name, template_number, generation_number, reference):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=24*mm, leftMargin=24*mm,
                            topMargin=27*mm, bottomMargin=24*mm, title="Procuração", author="Iustus")
    normal = ParagraphStyle("body", fontName="Iustus", fontSize=10.5, leading=16, spaceAfter=12,
                            textColor=colors.HexColor("#15243b"), splitLongWords=True)
    title = ParagraphStyle("title", parent=normal, fontName="IustusBold", fontSize=19, leading=24,
                           alignment=TA_CENTER, spaceAfter=20)
    small = ParagraphStyle("meta", parent=normal, fontSize=8, leading=12, textColor=colors.HexColor("#526079"))
    story = [Paragraph("PROCURAÇÃO", title),
             Paragraph(escape(f"Caso {reference} | Modelo {template_name} v{template_number} | Emissão {generation_number}"), small),
             HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#c3a66e")), Spacer(1, 7*mm)]
    for paragraph in body.split("\n"):
        story.append(Paragraph(escape(paragraph), normal) if paragraph.strip() else Spacer(1, 3*mm))
    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d7dce3"))
        canvas.line(24*mm, 19*mm, A4[0]-24*mm, 19*mm)
        canvas.setFont("Iustus", 8)
        canvas.setFillColor(colors.HexColor("#526079"))
        canvas.drawString(24*mm, 14*mm, f"Iustus | Caso {reference} | Modelo v{template_number}")
        canvas.drawRightString(A4[0]-24*mm, 14*mm, f"Página {document.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
