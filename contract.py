"""Genera el contrato de arrendamiento de salón de eventos — Celebra Sur, Hermosillo, Son."""
import io
from datetime import date
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

AZUL       = colors.HexColor("#1e3a8a")
AZUL_LIGHT = colors.HexColor("#dbeafe")
AZUL_MED   = colors.HexColor("#3b82f6")
GRIS       = colors.HexColor("#475569")
NEGRO      = colors.HexColor("#0f172a")
BORDE      = colors.HexColor("#cbd5e1")
ROJO_LIGHT = colors.HexColor("#fee2e2")


def _mes_es(m: int) -> str:
    return ["enero","febrero","marzo","abril","mayo","junio",
            "julio","agosto","septiembre","octubre","noviembre","diciembre"][m-1]


def _fecha_es(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
        return f"{d.day} de {_mes_es(d.month)} de {d.year}"
    except Exception:
        return iso


def _estilos():
    return {
        "titulo":    ParagraphStyle("t1", fontSize=17, fontName="Helvetica-Bold",
                                    textColor=AZUL, alignment=TA_CENTER, spaceAfter=3),
        "subtitulo": ParagraphStyle("t2", fontSize=10, fontName="Helvetica",
                                    textColor=GRIS, alignment=TA_CENTER, spaceAfter=2),
        "seccion":   ParagraphStyle("sec", fontSize=10, fontName="Helvetica-Bold",
                                    textColor=colors.white, spaceBefore=10, spaceAfter=5,
                                    backColor=AZUL, leftIndent=-6, rightIndent=-6,
                                    borderPad=4),
        "cuerpo":    ParagraphStyle("cb", fontSize=9.5, fontName="Helvetica",
                                    textColor=NEGRO, leading=14, spaceAfter=4,
                                    alignment=TA_JUSTIFY),
        "clausula":  ParagraphStyle("cl", fontSize=9.5, fontName="Helvetica",
                                    textColor=NEGRO, leading=14, spaceAfter=6,
                                    leftIndent=14, alignment=TA_JUSTIFY),
        "aviso":     ParagraphStyle("av", fontSize=9, fontName="Helvetica-BoldOblique",
                                    textColor=colors.HexColor("#7f1d1d"),
                                    backColor=ROJO_LIGHT, leading=13,
                                    leftIndent=6, rightIndent=6, spaceAfter=5,
                                    borderPad=4),
        "firma_lbl": ParagraphStyle("fl", fontSize=8.5, fontName="Helvetica",
                                    textColor=GRIS, alignment=TA_CENTER),
        "folio":     ParagraphStyle("fo", fontSize=8, fontName="Helvetica",
                                    textColor=GRIS, alignment=TA_CENTER),
    }


def generar_contrato(
    *,
    nombre_negocio: str,
    representante: str,
    arrendatario: str,
    tipo_evento: str,
    fecha_evento: str,
    hora_inicio: str,
    horas_servicio: int,
    costo_total: float,
    monto_apartado: float,
    fecha_apartado: str,
    saldo_pendiente: float,
    fecha_limite_pago: str,
    salon: str,
    alcohol: str,
    clausulas_extra: list,
    folio: str = "",
) -> bytes:

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=2.4*cm, rightMargin=2.4*cm,
        topMargin=1.8*cm, bottomMargin=2.2*cm,
        title=f"Contrato {arrendatario}",
    )
    st = _estilos()
    s = []

    hoy_str = _fecha_es(date.today().isoformat())
    fecha_ev_str = _fecha_es(fecha_evento)
    hora_fin = f"{int(hora_inicio.split(':')[0]) + horas_servicio:02d}:{hora_inicio.split(':')[1]}"

    # ── ENCABEZADO ─────────────────────────────────────────────────────────
    s.append(Paragraph(nombre_negocio.upper(), st["titulo"]))
    s.append(Paragraph("Contrato de Arrendamiento de Salón para Eventos", st["subtitulo"]))
    s.append(Paragraph(f"{salon}  ·  Hermosillo, Sonora", st["subtitulo"]))
    if folio:
        s.append(Paragraph(f"Folio: {folio}   |   Fecha de contrato: {hoy_str}", st["folio"]))
    s.append(Spacer(1, 0.3*cm))
    s.append(HRFlowable(width="100%", thickness=2.5, color=AZUL))
    s.append(Spacer(1, 0.3*cm))

    # ── PARTES ─────────────────────────────────────────────────────────────
    s.append(Paragraph("I. PARTES CONTRATANTES", st["seccion"]))
    partes = [
        ["ARRENDADOR:", nombre_negocio],
        ["Representante:", representante],
        ["Domicilio:", salon],
        ["", ""],
        ["ARRENDATARIO:", arrendatario],
    ]
    tp = Table(partes, colWidths=[4*cm, 12*cm])
    tp.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",  (0,0), (-1,-1), 9.5),
        ("TEXTCOLOR", (0,0), (0,-1), AZUL),
        ("TEXTCOLOR", (1,0), (1,-1), NEGRO),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[AZUL_LIGHT, colors.white]),
        ("GRID", (0,0), (-1,-1), 0.3, BORDE),
        ("PADDING", (0,0), (-1,-1), 5),
        ("SPAN", (0,3), (1,3)),
        ("BACKGROUND",(0,3),(1,3),colors.white),
    ]))
    s.append(tp)
    s.append(Spacer(1, 0.4*cm))

    # ── DATOS DEL EVENTO ───────────────────────────────────────────────────
    s.append(Paragraph("II. DATOS DEL EVENTO", st["seccion"]))
    ev_data = [
        ["Tipo de evento:", tipo_evento,        "Fecha:", fecha_ev_str],
        ["Horario:",        f"{hora_inicio} – {hora_fin} hrs",
         "Duración:",       f"{horas_servicio} horas continuas"],
        ["Salón:",          salon,               "Folio:", folio],
    ]
    te = Table(ev_data, colWidths=[3.5*cm, 7.5*cm, 3*cm, 5.5*cm])
    te.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), AZUL),
        ("TEXTCOLOR", (2,0), (2,-1), AZUL),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[AZUL_LIGHT, colors.white]),
        ("GRID", (0,0), (-1,-1), 0.3, BORDE),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    s.append(te)
    s.append(Spacer(1, 0.4*cm))

    # ── COSTO Y PAGOS ─────────────────────────────────────────────────────
    s.append(Paragraph("III. MONTO Y FORMA DE PAGO", st["seccion"]))
    pagos = [
        ["Concepto", "Monto"],
        ["Costo total del arrendamiento", f"${costo_total:,.2f}"],
        ["Anticipo / Apartado pagado", f"${monto_apartado:,.2f}"],
        ["Saldo pendiente por liquidar", f"${saldo_pendiente:,.2f}"],
    ]
    tpag = Table(pagos, colWidths=[11*cm, 5.5*cm])
    tpag.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",  (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",  (0,0), (-1,-1), 9.5),
        ("BACKGROUND",(0,0),(-1,0), AZUL),
        ("TEXTCOLOR", (0,0),(-1,0), colors.white),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, AZUL_LIGHT]),
        ("GRID", (0,0), (-1,-1), 0.4, BORDE),
        ("ALIGN", (1,0),(1,-1), "RIGHT"),
        ("PADDING", (0,0),(-1,-1), 6),
        ("FONTNAME",  (0,-1),(-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,-1),(-1,-1), AZUL),
    ]))
    s.append(tpag)
    s.append(Spacer(1, 0.2*cm))
    s.append(Paragraph(
        f"El saldo de <b>${saldo_pendiente:,.2f}</b> deberá liquidarse a más tardar el "
        f"<b>{fecha_limite_pago}</b>. El incumplimiento en el pago total previo al evento "
        f"faculta al arrendador a cancelar el servicio sin reembolso del anticipo.",
        st["cuerpo"]
    ))
    s.append(Spacer(1, 0.3*cm))

    # ── CONDICIONES GENERALES ─────────────────────────────────────────────
    s.append(Paragraph("IV. CONDICIONES GENERALES DEL ARRENDAMIENTO", st["seccion"]))

    condiciones = [
        ("1", "DURACIÓN Y PUNTUALIDAD",
         f"El servicio contratado tiene una duración de <b>{horas_servicio} horas</b> "
         f"({hora_inicio} a {hora_fin} hrs). El tiempo adicional causará un cargo extra "
         f"de acuerdo a la tarifa vigente. EL ARRENDATARIO se compromete a desalojar las "
         f"instalaciones puntualmente a la hora de término pactada."),

        ("2", "BEBIDAS Y ALCOHOL",
         f"Las partes acuerdan que el evento se realizará: <b>{alcohol}</b>. "
         + ("En caso de permitirse alcohol, EL ARRENDATARIO asume plena responsabilidad "
            "civil y penal de garantizar que ningún menor de 18 años consuma bebidas "
            "alcohólicas, conforme a la Ley para la Protección de Niñas, Niños y "
            "Adolescentes del Estado de Sonora. Cualquier incidente derivado del consumo "
            "de alcohol será responsabilidad exclusiva del arrendatario."
            if "con alcohol" in alcohol.lower() else
            "Queda estrictamente prohibida la introducción y consumo de cualquier tipo "
            "de bebida alcohólica dentro y en los alrededores del salón. El incumplimiento "
            "faculta al arrendador a suspender el evento de inmediato sin derecho a "
            "reembolso.")),

        ("3", "PROHIBICIÓN DE PIROTECNIA",
         "Queda <b>estrictamente prohibido</b> el uso de cohetes, fuegos artificiales, "
         "bengalas, confeti de papel o metálico, serpentinas y cualquier material "
         "pirotécnico dentro y en los alrededores del salón, conforme al Reglamento "
         "de Protección Civil del Municipio de Hermosillo. El incumplimiento causará la "
         "suspensión inmediata del evento, siendo responsabilidad del arrendatario "
         "cualquier daño personal o material resultante."),

        ("4", "RESPONSABILIDAD CIVIL Y DESLINDE",
         f"EL ARRENDATARIO libera expresamente a <b>{nombre_negocio}</b>, a sus "
         f"propietarios, representantes y empleados de cualquier responsabilidad civil, "
         f"penal o administrativa por daños, lesiones, pérdidas o accidentes que "
         f"sufran los asistentes al evento, incluyendo riñas, accidentes, robos, "
         f"intoxicaciones o cualquier incidente ocurrido dentro o fuera de las "
         f"instalaciones durante el horario contratado. EL ARRENDATARIO es el único "
         f"responsable de la conducta de sus invitados."),

        ("5", "SEGURIDAD Y VIGILANCIA",
         f"EL ARRENDATARIO es responsable de contratar, si lo considera necesario, "
         f"el personal de seguridad y vigilancia para su evento. "
         f"<b>{nombre_negocio}</b> no se hace responsable de objetos olvidados, "
         f"robados o extraviados durante el evento, ni de vehículos estacionados "
         f"en los alrededores del salón. Se recomienda no dejar objetos de valor "
         f"sin supervisión."),

        ("6", "DAÑOS A LAS INSTALACIONES",
         "EL ARRENDATARIO será responsable de cubrir el costo total de cualquier "
         "daño ocasionado a las instalaciones, mobiliario, equipo de sonido, "
         "iluminación, cristalería o cualquier bien propiedad del arrendador, "
         "ocasionado por él mismo o sus invitados. Los daños serán valorados y "
         "cobrados al concluir el evento o en un plazo no mayor a 5 días hábiles."),

        ("7", "DECORACIÓN Y ACCESO PREVIO",
         "El acceso para instalación de decoración deberá coordinarse previamente "
         "con el arrendador. Está prohibido clavar, perforar, pintar, encolar o "
         "dañar paredes, techos, pisos o mobiliario del salón. El uso de veladoras "
         "o velas requiere autorización previa por escrito. El arrendador no se "
         "responsabiliza de la decoración contratada por el arrendatario con "
         "terceros proveedores."),

        ("8", "CAPACIDAD MÁXIMA Y AFORO",
         "EL ARRENDATARIO se compromete a respetar el aforo máximo permitido por "
         "el salón y por las disposiciones de Protección Civil del Estado de Sonora. "
         "El exceso de aforo podrá resultar en la suspensión inmediata del evento "
         "por parte de las autoridades competentes, sin responsabilidad para el "
         "arrendador y sin derecho a reembolso."),

        ("9", "CANCELACIONES Y DEVOLUCIONES",
         "Cancelaciones con <b>más de 30 días naturales</b> de anticipación: "
         "el anticipo podrá aplicarse a una nueva fecha sujeta a disponibilidad. "
         "Cancelaciones con <b>menos de 30 días</b>: el anticipo no es reembolsable "
         "y se aplicará como pena convencional. En caso de cancelación por causa "
         "de fuerza mayor debidamente documentada (desastre natural, decreto "
         "gubernamental, fallecimiento), las partes acordarán la reposición del "
         "evento o la devolución parcial del anticipo."),

        ("10", "CASO FORTUITO Y FUERZA MAYOR",
         f"Ninguna de las partes será responsable por el incumplimiento de sus "
         f"obligaciones cuando éste sea causado por caso fortuito o fuerza mayor, "
         f"incluyendo desastres naturales, epidemias declaradas por autoridad "
         f"competente, actos de autoridad o cualquier circunstancia fuera del "
         f"control razonable de las partes. En dicho supuesto, las partes "
         f"acordarán de buena fe una solución equitativa."),

        ("11", "RUIDO Y NORMATIVIDAD MUNICIPAL",
         "EL ARRENDATARIO y sus proveedores de entretenimiento (DJ, bandas, "
         "grupos musicales) deberán cumplir con los límites de decibeles "
         "establecidos por el Reglamento de Bando de Policía y Gobierno del "
         "Municipio de Hermosillo, Sonora. El arrendador podrá solicitar la "
         "reducción del volumen o la suspensión de la música en caso de "
         "incumplimiento o queja fundada de vecinos."),

        ("12", "JURISDICCIÓN Y LEGISLACIÓN APLICABLE",
         "Para todo lo no previsto en el presente contrato, las partes se "
         "someten a las leyes aplicables del Estado de Sonora y a la "
         "jurisdicción de los Tribunales competentes de la Ciudad de "
         "<b>Hermosillo, Sonora</b>, renunciando expresamente a cualquier "
         "otro fuero que pudiera corresponderles por razón de sus domicilios "
         "presentes o futuros."),
    ]

    for num, titulo_c, texto in condiciones:
        s.append(KeepTogether([
            Paragraph(f"<b>Cláusula {num}. — {titulo_c}</b>", st["cuerpo"]),
            Paragraph(texto, st["clausula"]),
        ]))

    # ── CLÁUSULAS ADICIONALES ─────────────────────────────────────────────
    if clausulas_extra:
        s.append(Paragraph("V. CLÁUSULAS ADICIONALES", st["seccion"]))
        for i, texto_e in enumerate(clausulas_extra, start=len(condiciones)+1):
            if texto_e.strip():
                s.append(KeepTogether([
                    Paragraph(f"<b>Cláusula {i}.</b>", st["cuerpo"]),
                    Paragraph(texto_e.strip(), st["clausula"]),
                ]))

    # ── AVISO IMPORTANTE ─────────────────────────────────────────────────
    s.append(Spacer(1, 0.3*cm))
    s.append(Paragraph(
        "⚠️  IMPORTANTE: Al realizar el pago del anticipo, EL ARRENDATARIO declara "
        "haber leído, entendido y aceptado la totalidad de las cláusulas del presente "
        "contrato. La ignorancia de las mismas no exime de su cumplimiento.",
        st["aviso"]
    ))

    # ── FIRMAS ────────────────────────────────────────────────────────────
    firma_nombre = ParagraphStyle("fn", fontSize=11, fontName="Helvetica-Bold",
                                   textColor=AZUL, alignment=TA_CENTER, leading=14)
    firma_rol    = ParagraphStyle("fr", fontSize=8.5, fontName="Helvetica",
                                   textColor=GRIS, alignment=TA_CENTER, leading=12)

    s.append(Spacer(1, 1.2*cm))
    s.append(HRFlowable(width="100%", thickness=0.8, color=BORDE))
    s.append(Spacer(1, 0.2*cm))
    firmas_data = [
        # líneas de firma
        ["_"*40, "   ", "_"*40],
        # nombres debajo de la línea
        [Paragraph(f"<b>{representante or nombre_negocio}</b>", firma_nombre), "",
         Paragraph(f"<b>{arrendatario}</b>", firma_nombre)],
        # roles
        [Paragraph(f"{nombre_negocio}", firma_rol), "",
         Paragraph(f"ARRENDATARIO", firma_rol)],
        [Paragraph("EL ARRENDADOR", firma_rol), "",
         Paragraph(f"Quien renta el salón", firma_rol)],
    ]
    tf = Table(firmas_data, colWidths=[7.5*cm, 1.5*cm, 7.5*cm])
    tf.setStyle(TableStyle([
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "BOTTOM"),
        ("FONTSIZE",   (0,0), (-1,0),  9),
        ("TOPPADDING", (0,1), (-1,-1), 4),
        # resaltar columna del arrendatario
        ("BACKGROUND", (2,1), (2,3), AZUL_LIGHT),
        ("ROUNDEDCORNERS", [4]),
    ]))
    s.append(tf)
    s.append(Spacer(1, 0.5*cm))
    s.append(HRFlowable(width="100%", thickness=0.4, color=BORDE))
    s.append(Spacer(1, 0.15*cm))
    s.append(Paragraph(
        f"Contrato generado el {hoy_str}  ·  {nombre_negocio}  ·  Hermosillo, Sonora",
        st["folio"]
    ))

    doc.build(s)
    return buf.getvalue()
