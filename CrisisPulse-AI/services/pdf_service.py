"""
services/pdf_service.py
Generates downloadable PDF briefings for crisis analysis results using ReportLab.
"""

import os
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_crisis_pdf(analysis_id: int, result: dict) -> str:
    temp_dir = tempfile.gettempdir()
    pdf_path = os.path.join(temp_dir, f"crisis_briefing_{analysis_id}.pdf")

    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=20, leading=24,
                                  textColor=colors.HexColor("#0f172a"), alignment=0, fontName="Helvetica-Bold")
    header_sub = ParagraphStyle("HeaderSub", parent=styles["Normal"], fontSize=10,
                                 textColor=colors.HexColor("#64748b"), spaceAfter=12)
    heading_style = ParagraphStyle("SectionHeading", parent=styles["Heading2"], fontSize=13, leading=16,
                                    textColor=colors.HexColor("#1e293b"), spaceBefore=10, spaceAfter=6,
                                    fontName="Helvetica-Bold")
    body_style = ParagraphStyle("BodyTextCustom", parent=styles["Normal"], fontSize=10, leading=14,
                                 textColor=colors.HexColor("#334155"), spaceAfter=6)
    alert_style = ParagraphStyle("AlertBoxText", parent=styles["Normal"], fontSize=11, leading=15,
                                  textColor=colors.HexColor("#991b1b"), fontName="Helvetica-Bold")
    link_style = ParagraphStyle("LinkText", parent=styles["Normal"], fontSize=9, leading=13,
                                 textColor=colors.HexColor("#2563eb"))

    elements = []
    elements.append(Paragraph("🚨 EMERGENCY CRISIS BRIEFING", title_style))
    elements.append(Paragraph(f"Analysis ID: #{analysis_id} | CrisisPulse AI — Groq + Tavily Multi-Agent System", header_sub))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    sev = str(result.get("severity", "MEDIUM")).upper()
    sev_color = {
        "LOW": colors.HexColor("#16a34a"),
        "MEDIUM": colors.HexColor("#ca8a04"),
        "HIGH": colors.HexColor("#ea580c"),
        "CRITICAL": colors.HexColor("#dc2626"),
    }.get(sev, colors.HexColor("#2563eb"))

    meta_data = [
        [Paragraph(f"<b>Severity Level:</b> <font color='{sev_color.hexval()}'><b>{sev}</b></font>", body_style),
         Paragraph(f"<b>Crisis Type:</b> {result.get('crisis_type', 'Other')}", body_style)],
        [Paragraph(f"<b>Location:</b> {result.get('location', 'Unknown')}", body_style),
         Paragraph(f"<b>Date/Time:</b> {result.get('date_time', 'Not specified')}", body_style)],
        [Paragraph(f"<b>Affected People:</b> {result.get('affected_people', 'Unknown')}", body_style),
         Paragraph(f"<b>Casualties:</b> {result.get('casualties', 'None reported')}", body_style)],
    ]
    t = Table(meta_data, colWidths=[270, 270])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    alert_msg = result.get("alert_message", "")
    if alert_msg:
        alert_table = Table([[Paragraph(f"⚠️ <b>ALERT:</b> {alert_msg}", alert_style)]], colWidths=[540])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#fca5a5")),
        ]))
        elements.append(alert_table)
        elements.append(Spacer(1, 10))

    elements.append(Paragraph("📋 Situation Summary", heading_style))
    elements.append(Paragraph(result.get("summary", "N/A"), body_style))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("🧠 Severity Reasoning", heading_style))
    elements.append(Paragraph(result.get("severity_reason", "N/A"), body_style))
    elements.append(Spacer(1, 8))

    # Live verification section (Tavily)
    verification_note = result.get("verification_note")
    if verification_note:
        corroborated = result.get("corroborated", "unknown")
        badge = {"true": "✅ Corroborated", "false": "⚠️ Not corroborated"}.get(str(corroborated).lower(), "ℹ️ Unverified")
        elements.append(Paragraph(f"🌐 Live Verification — {badge}", heading_style))
        elements.append(Paragraph(verification_note, body_style))
        sources = result.get("live_sources", []) or []
        for s in sources:
            title = s.get("title", "Source")
            url = s.get("url", "")
            if url:
                elements.append(Paragraph(f'• <a href="{url}" color="#2563eb">{title}</a> — {url}', link_style))
        elements.append(Spacer(1, 8))

    key_points = result.get("key_points", []) or []
    if key_points:
        elements.append(Paragraph("🔑 Key Impact Points", heading_style))
        for kp in key_points:
            elements.append(Paragraph(f"• {kp}", body_style))
        elements.append(Spacer(1, 8))

    recs = result.get("safety_recommendations", []) or []
    if recs:
        elements.append(Paragraph("✅ Safety & Action Recommendations", heading_style))
        for r in recs:
            elements.append(Paragraph(f"✔ {r}", body_style))
        elements.append(Spacer(1, 8))

    doc.build(elements)
    return pdf_path
