"""Genera un PDF con el resumen completo del dashboard — Control Financiero.

Uso:  python3 reporte.py [ruta_de_salida.pdf]

Lee los datos vivos de Supabase (vía database.py) y el histórico de los CSV de data/.
El PDF que produce trae información financiera privada: no lo subas al repo.
"""
import io
import sys
import csv
from pathlib import Path
from datetime import date
from collections import defaultdict

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak,
    KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

import database as db

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"

AZUL   = colors.HexColor("#1e3a8a")
AZUL_L = colors.HexColor("#dbeafe")
VERDE  = colors.HexColor("#166534")
VERDE_L= colors.HexColor("#dcfce7")
ROJO   = colors.HexColor("#991b1b")
ROJO_L = colors.HexColor("#fee2e2")
AMBAR_L= colors.HexColor("#fef3c7")
GRIS   = colors.HexColor("#475569")
NEGRO  = colors.HexColor("#0f172a")
BORDE  = colors.HexColor("#cbd5e1")
ZEBRA  = colors.HexColor("#f8fafc")

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

E = {
    "titulo":  ParagraphStyle("t", fontSize=22, fontName="Helvetica-Bold", leading=27,
                              textColor=AZUL, alignment=TA_CENTER, spaceAfter=7),
    "sub":     ParagraphStyle("s", fontSize=10.5, fontName="Helvetica", leading=15,
                              textColor=GRIS, alignment=TA_CENTER, spaceAfter=2),
    # leading holgado: si no, la franja azul le come la parte de arriba al texto
    "seccion": ParagraphStyle("sec", fontSize=11.5, fontName="Helvetica-Bold", leading=16,
                              textColor=colors.white, spaceBefore=15, spaceAfter=9,
                              backColor=AZUL, leftIndent=-6, rightIndent=-6, borderPad=6),
    "sub2":    ParagraphStyle("s2", fontSize=10, fontName="Helvetica-Bold",
                              textColor=AZUL, spaceBefore=9, spaceAfter=4),
    "cuerpo":  ParagraphStyle("c", fontSize=9, fontName="Helvetica",
                              textColor=NEGRO, leading=13, spaceAfter=5),
    "nota":    ParagraphStyle("n", fontSize=8, fontName="Helvetica-Oblique",
                              textColor=GRIS, leading=11, spaceAfter=4),
    "alerta":  ParagraphStyle("a", fontSize=9, fontName="Helvetica-Bold",
                              textColor=ROJO, backColor=ROJO_L, leading=13,
                              leftIndent=6, rightIndent=6, spaceAfter=6, borderPad=5),
    "ok":      ParagraphStyle("o", fontSize=9, fontName="Helvetica-Bold",
                              textColor=VERDE, backColor=VERDE_L, leading=13,
                              leftIndent=6, rightIndent=6, spaceAfter=6, borderPad=5),
}


def mxn(v, dec=0):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"${abs(v):,.{dec}f}"
    return f"-{s}" if v < 0 else s


def leer_csv(nombre):
    ruta = DATA / nombre
    return list(csv.DictReader(open(ruta, encoding="utf-8"))) if ruta.exists() else []


def tabla(datos, anchos, alinea_der=(), encabezado=True, zebra=True, tam=8.2):
    t = Table(datos, colWidths=anchos, repeatRows=1 if encabezado else 0)
    est = [
        ("FONT",       (0, 0), (-1, -1), "Helvetica", tam),
        ("TEXTCOLOR",  (0, 0), (-1, -1), NEGRO),
        ("GRID",       (0, 0), (-1, -1), 0.4, BORDE),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]
    if encabezado:
        est += [("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONT",       (0, 0), (-1, 0), "Helvetica-Bold", tam)]
    if zebra:
        for i in range(1 if encabezado else 0, len(datos)):
            if i % 2 == (0 if encabezado else 1):
                est.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    for c in alinea_der:
        est.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(est))
    return t


def tarjetas(items):
    """Fila de KPIs: items = [(etiqueta, valor, pie, color_fondo)]"""
    fila_lbl, fila_val, fila_pie, est = [], [], [], []
    for i, (lbl, val, pie, bg) in enumerate(items):
        fila_lbl.append(Paragraph(f'<font size=6.5 color="#475569">{lbl.upper()}</font>', E["cuerpo"]))
        fila_val.append(Paragraph(f'<font size=14><b>{val}</b></font>', E["cuerpo"]))
        fila_pie.append(Paragraph(f'<font size=6.5 color="#475569">{pie}</font>', E["cuerpo"]))
        est.append(("BACKGROUND", (i, 0), (i, 2), bg))
    t = Table([fila_lbl, fila_val, fila_pie],
              colWidths=[18.0 * cm / len(items)] * len(items))
    t.setStyle(TableStyle(est + [
        ("BOX", (0, 0), (-1, -1), 0.4, BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def barras(pares, ancho=17.5 * cm, alto=3.2 * cm, color=AZUL, fmt=mxn):
    """Gráfica de barras hecha con una tabla: cada barra es una celda coloreada."""
    if not pares:
        return Spacer(1, 1)
    tope = max(abs(v) for _, v in pares) or 1
    filas_barra, etiquetas, valores, est = [], [], [], []
    for i, (k, v) in enumerate(pares):
        h = max(0.12, abs(v) / tope) * alto
        celda = Table([[""]], colWidths=[ancho / len(pares) - 4], rowHeights=[h])
        celda.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ROJO if v < 0 else color),
            ("BOX", (0, 0), (-1, -1), 0, colors.white)]))
        filas_barra.append(celda)
        etiquetas.append(Paragraph(f'<font size=6.5>{k}</font>', E["cuerpo"]))
        valores.append(Paragraph(f'<font size=6.5><b>{fmt(v)}</b></font>', E["cuerpo"]))
    t = Table([valores, filas_barra, etiquetas], colWidths=[ancho / len(pares)] * len(pares))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
        ("VALIGN", (0, 1), (-1, 1), "BOTTOM"),
        ("VALIGN", (0, 2), (-1, 2), "TOP"),
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LINEBELOW", (0, 1), (-1, 1), 0.6, BORDE),
    ]))
    return t


# ── Datos ────────────────────────────────────────────────────────────────────
def reunir():
    d = {}
    d["patrimonio"] = db.get_patrimonio() or []
    d["eventos"]    = db.get_eventos() or []
    d["rentas"]     = db.get_rentas() or []
    d["autos_app"]  = db.get_autos() or []
    d["fact"]       = db.get_facturaciones() or []
    d["gastos_app"] = db.get_gastos() or []
    d["hist"]       = leer_csv("historico_autos.csv")
    d["ing"]        = leer_csv("ingresos_historico.csv")
    d["gneg"]       = leer_csv("gastos_negocio.csv")
    d["meses"]      = {int(r["anio"]): int(r["meses_con_hoja"])
                       for r in leer_csv("historico_autos_meses.csv")}
    return d


def caja_por_anio(d):
    """Utilidad de autos + otros ingresos - gastos del negocio, por año."""
    A, I, G = defaultdict(float), defaultdict(float), defaultdict(float)
    for r in d["hist"]:
        A[int(r["anio"])] += float(r["util_neta_calc"])
    for r in d["ing"]:
        I[int(r["anio"])] += float(r["monto"])
    for r in d["gneg"]:
        G[int(r["anio"])] += float(r["gastos"])
    ultimo_gasto = max(G) if G else None
    filas = []
    for a in sorted(set(A) | set(I)):
        if a < 2021:
            continue
        ms = d["meses"].get(a, 12)
        g, estimado = G.get(a, 0.0), False
        if not g and ultimo_gasto:
            g, estimado = G[ultimo_gasto] / 12 * ms, True
        filas.append(dict(anio=a, meses=ms, autos=A[a], otros=I[a],
                          entra=A[a] + I[a], gastos=g, estimado=estimado,
                          res=A[a] + I[a] - g, res_mes=(A[a] + I[a] - g) / ms))
    return filas


# ── Secciones ────────────────────────────────────────────────────────────────
def portada(h, d):
    hoy = date.today()
    h.append(Spacer(1, 1.6 * cm))
    h.append(Paragraph("Control Financiero", E["titulo"]))
    h.append(Paragraph("Resumen completo del dashboard", E["sub"]))
    h.append(Paragraph(f"Gustavo Félix · Hermosillo, Sonora · "
                       f"{hoy.day} de {MESES[hoy.month-1].lower()} de {hoy.year}", E["sub"]))
    h.append(Spacer(1, 0.4 * cm))
    h.append(HRFlowable(width="100%", thickness=1.2, color=AZUL))
    h.append(Spacer(1, 0.5 * cm))

    act = sum(float(p["monto"]) for p in d["patrimonio"] if p["tipo"] == "Activo")
    pas = sum(float(p["monto"]) for p in d["patrimonio"] if p["tipo"] == "Pasivo")
    liq = sum(float(p["monto"]) for p in d["patrimonio"]
              if p["tipo"] == "Activo" and p.get("liquido"))
    caja = caja_por_anio(d)
    ult = caja[-1] if caja else None
    aire = (liq / abs(ult["res_mes"])) if ult and ult["res_mes"] < 0 else None

    h.append(tarjetas([
        ("Patrimonio neto", mxn(act - pas), f"Activos {mxn(act)}", AZUL_L),
        ("Líquido", mxn(liq), f"{liq/(act-pas)*100:.1f}% del patrimonio", AMBAR_L),
        ("Resultado mensual", mxn(ult["res_mes"]) if ult else "—",
         f"Ritmo {ult['anio']}" if ult else "", ROJO_L if ult and ult["res_mes"] < 0 else VERDE_L),
        ("Meses de aire", f"{aire:.1f}" if aire else "—",
         "Líquido ÷ pérdida mensual" if aire else "Sin pérdida", ROJO_L if aire else VERDE_L),
    ]))
    h.append(Spacer(1, 0.5 * cm))

    if ult and ult["res_mes"] < 0:
        h.append(Paragraph(
            f"Al ritmo de {ult['anio']} el negocio pierde {mxn(abs(ult['res_mes']))} al mes. "
            f"Con {mxn(liq)} líquidos, eso da alrededor de {aire:.1f} meses de operación "
            f"antes de quedarse sin caja.", E["alerta"]))

    h.append(Paragraph(
        "Este documento junta lo que hay en el dashboard: patrimonio, situación de caja, "
        "el histórico del lote de autos reconstruido del Excel AUTO FACIL (2018–2026), "
        "los otros ingresos por categoría, Celebra Sur y los movimientos capturados en la app.",
        E["cuerpo"]))


def sec_patrimonio(h, d):
    h.append(Paragraph("1. Patrimonio", E["seccion"]))
    p = d["patrimonio"]
    act = [x for x in p if x["tipo"] == "Activo"]
    pas = [x for x in p if x["tipo"] == "Pasivo"]
    ta, tp = sum(float(x["monto"]) for x in act), sum(float(x["monto"]) for x in pas)

    h.append(Paragraph("Activos", E["sub2"]))
    filas = [["Concepto", "Categoría", "Monto", "Líquido"]]
    for x in sorted(act, key=lambda y: -float(y["monto"])):
        filas.append([x["nombre"], x.get("categoria") or "—", mxn(x["monto"]),
                      "Sí" if x.get("liquido") else "No"])
    filas.append(["TOTAL ACTIVOS", "", mxn(ta), ""])
    t = tabla(filas, [7.4*cm, 4.4*cm, 3.4*cm, 2.3*cm], alinea_der=(2,))
    t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                           ("BACKGROUND", (0,-1), (-1,-1), AZUL_L)]))
    h.append(t)

    h.append(Paragraph("Pasivos", E["sub2"]))
    filas = [["Concepto", "Categoría", "Monto", "Nota"]]
    for x in sorted(pas, key=lambda y: -float(y["monto"])):
        nota = (x.get("notas") or "—")
        filas.append([x["nombre"], x.get("categoria") or "—", mxn(x["monto"]),
                      Paragraph(f'<font size=6.8>{nota[:70]}</font>', E["cuerpo"])])
    filas.append(["TOTAL PASIVOS", "", mxn(tp), ""])
    t = tabla(filas, [5.2*cm, 3.6*cm, 3.0*cm, 5.7*cm], alinea_der=(2,))
    t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                           ("BACKGROUND", (0,-1), (-1,-1), ROJO_L)]))
    h.append(t)

    h.append(Spacer(1, 0.3 * cm))
    h.append(tarjetas([
        ("Activos", mxn(ta), f"{len(act)} conceptos", AZUL_L),
        ("Pasivos", mxn(tp), f"{len(pas)} conceptos", ROJO_L),
        ("Patrimonio neto", mxn(ta - tp), "Activos − pasivos", VERDE_L),
    ]))


def sec_caja(h, d):
    h.append(Paragraph("2. Situación de caja", E["seccion"]))
    caja = caja_por_anio(d)
    filas = [["Año", "Meses", "Utilidad autos", "Otros ingresos", "Entra", "Gastos", "Resultado", "Por mes"]]
    for f in caja:
        filas.append([str(f["anio"]), str(f["meses"]), mxn(f["autos"]), mxn(f["otros"]),
                      mxn(f["entra"]), mxn(f["gastos"]) + ("*" if f["estimado"] else ""),
                      mxn(f["res"]), mxn(f["res_mes"])])
    t = tabla(filas, [1.5*cm, 1.3*cm, 2.9*cm, 2.9*cm, 2.7*cm, 2.6*cm, 2.6*cm, 2.2*cm],
              alinea_der=(1,2,3,4,5,6,7))
    est = []
    for i, f in enumerate(caja, start=1):
        if f["res"] < 0:
            est += [("TEXTCOLOR", (6, i), (7, i), ROJO),
                    ("FONT", (6, i), (7, i), "Helvetica-Bold", 8.2)]
    t.setStyle(TableStyle(est))
    h.append(t)
    if any(f["estimado"] for f in caja):
        h.append(Paragraph("* Gasto estimado al ritmo del último año con dato real; el "
                           "AUTO FACIL ANUAL solo trae la columna de gastos hasta 2025.", E["nota"]))
    h.append(Spacer(1, 0.3 * cm))
    h.append(KeepTogether([Paragraph("Resultado por mes", E["sub2"]),
                           barras([(str(f["anio"]), f["res_mes"]) for f in caja], color=VERDE)]))
    h.append(Spacer(1, 0.2 * cm))
    h.append(Paragraph(
        "Hasta 2024 el negocio dejaba dinero cada mes. 2025 es el primer año en pérdida y "
        "2026 la profundiza: el lote produce menos y los gastos no bajaron al mismo ritmo.",
        E["cuerpo"]))


def sec_autos(h, d):
    h.append(Paragraph("3. Lote de autos — histórico 2018 a 2026", E["seccion"]))
    hist = d["hist"]
    A = defaultdict(lambda: dict(n=0, v=0.0, c=0.0, ub=0.0, co=0.0, ga=0.0))
    for r in hist:
        a = A[int(r["anio"])]
        a["n"] += 1
        a["v"] += float(r["venta"]); a["c"] += float(r["costo"])
        a["ub"] += float(r["util_bruta_hoja"]); a["co"] += float(r["comision"])
        a["ga"] += float(r["gastos"])
    filas = [["Año", "Meses", "Unidades", "Ventas", "Costo", "Utilidad neta", "Ticket", "Margen", "Autos/mes"]]
    for k in sorted(A):
        a = A[k]; ms = d["meses"].get(k, 12); un = a["ub"] - a["co"] - a["ga"]
        filas.append([str(k), str(ms), str(a["n"]), mxn(a["v"]), mxn(a["c"]), mxn(un),
                      mxn(a["v"]/a["n"]), f"{un/a['v']*100:.1f}%", f"{a['n']/ms:.1f}"])
    tot_n = sum(a["n"] for a in A.values()); tot_v = sum(a["v"] for a in A.values())
    tot_u = sum(a["ub"] - a["co"] - a["ga"] for a in A.values())
    filas.append(["TOTAL", "", str(tot_n), mxn(tot_v), "", mxn(tot_u), "", "", ""])
    t = tabla(filas, [1.4*cm, 1.2*cm, 1.7*cm, 3.0*cm, 2.8*cm, 2.8*cm, 2.2*cm, 1.6*cm, 1.8*cm],
              alinea_der=(1,2,3,4,5,6,7,8))
    t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                           ("BACKGROUND", (0,-1), (-1,-1), AZUL_L)]))
    h.append(t)
    h.append(Spacer(1, 0.3 * cm))
    h.append(KeepTogether([Paragraph("Unidades vendidas por año", E["sub2"]),
                           barras([(str(k), A[k]["n"]) for k in sorted(A)],
                                  fmt=lambda v: f"{int(v)}")]))
    h.append(Spacer(1, 0.2 * cm))
    h.append(Paragraph(
        f"{tot_n} autos reconstruidos unidad por unidad del Excel AUTO FACIL. Cada auto cuenta "
        "una sola vez aunque se repita en las hojas de los meses siguientes. El pico fue 2022 "
        "con 125 unidades; desde ahí el volumen cayó cuatro años seguidos, aunque el ticket "
        "promedio subió y el margen se recuperó. 2018 (11 meses), 2020 (9) y 2026 (5) están "
        "incompletos en el Excel.", E["cuerpo"]))


def sec_ingresos(h, d):
    h.append(Paragraph("4. Otros ingresos", E["seccion"]))
    ing = d["ing"]
    CATS = ["Casas", "Local", "Facturaciones", "Otros"]
    A = defaultdict(lambda: defaultdict(float))
    for r in ing:
        A[int(r["anio"])][r["categoria"]] += float(r["monto"])
    filas = [["Año"] + CATS + ["Total"]]
    tot = defaultdict(float)
    for a in sorted(A):
        s = sum(A[a][c] for c in CATS)
        filas.append([str(a)] + [mxn(A[a][c]) for c in CATS] + [mxn(s)])
        for c in CATS:
            tot[c] += A[a][c]
    filas.append(["TOTAL"] + [mxn(tot[c]) for c in CATS] + [mxn(sum(tot.values()))])
    t = tabla(filas, [1.8*cm, 3.3*cm, 2.7*cm, 3.4*cm, 3.0*cm, 3.3*cm], alinea_der=(1,2,3,4,5))
    t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                           ("BACKGROUND", (0,-1), (-1,-1), AZUL_L)]))
    h.append(t)

    h.append(Paragraph("Comparativa de las propiedades rentadas", E["sub2"]))
    P = defaultdict(lambda: [0, 0.0, []])
    for r in ing:
        if r["categoria"] in ("Casas", "Local"):
            p = P[r["detalle"]]
            p[0] += 1; p[1] += float(r["monto"])
            p[2].append(int(r["anio"]) * 100 + int(r["mes"]))
    filas = [["Propiedad", "Meses anotados", "Total cobrado", "Promedio mensual", "Primer registro"]]
    for k, (n, s, per) in sorted(P.items(), key=lambda kv: -kv[1][1]):
        pm = min(per)
        filas.append([k, str(n), mxn(s), mxn(s/n), f"{MESES[pm % 100 - 1][:3]} {pm // 100}"])
    h.append(tabla(filas, [4.6*cm, 3.2*cm, 3.4*cm, 3.6*cm, 3.0*cm], alinea_der=(1,2,3)))
    h.append(Paragraph("El local va aparte del total de Casas en la tabla de arriba, pero se "
                       "incluye aquí para verlo junto a las demás propiedades.", E["nota"]))

    g = {int(r["anio"]): float(r["gastos"]) for r in d["gneg"]}
    if g:
        h.append(Paragraph("Otros ingresos contra los gastos del negocio", E["sub2"]))
        I = {a: sum(A[a][c] for c in CATS) for a in A}
        aa = sorted(set(I) & set(g))
        filas = [["Año", "Otros ingresos", "Gastos del negocio", "Cubren"]]
        for a in aa:
            filas.append([str(a), mxn(I[a]), mxn(g[a]), f"{I[a]/g[a]*100:.0f}%"])
        h.append(tabla(filas, [2.4*cm, 4.6*cm, 5.0*cm, 5.8*cm], alinea_der=(1,2,3)))
        h.append(Paragraph(
            "Las rentas y facturaciones ya pagan alrededor de un tercio de todos los gastos del "
            "negocio, cuando en 2022 pagaban el 6%. Es el ingreso que menos depende de tener "
            "capital.", E["cuerpo"]))
    h.append(Paragraph(
        "De 2023 a 2025 estos datos salen del AUTO FACIL ANUAL, donde vienen ya separados por "
        "columna; el resto se reconstruyó de los bloques de las hojas mensuales. Solo aparecen "
        "los meses en que quedaron anotados.", E["nota"]))


def sec_celebra(h, d):
    h.append(Paragraph("5. Celebra Sur — jardín de eventos", E["seccion"]))
    ev = [e for e in d["eventos"] if (e.get("fecha_evento") or "")[:4].isdigit()]
    M = defaultdict(lambda: [0, 0.0, 0.0])
    for e in ev:
        k = (e["fecha_evento"] or "")[:7]
        M[k][0] += 1
        M[k][1] += float(e.get("costo_total") or 0)
        M[k][2] += float(e.get("utilidad") or 0)
    filas = [["Mes", "Eventos", "Facturado", "Utilidad capturada"]]
    for k in sorted(M):
        n, f, u = M[k]
        filas.append([k, str(n), mxn(f), mxn(u)])
    tn = sum(v[0] for v in M.values()); tf = sum(v[1] for v in M.values())
    tu = sum(v[2] for v in M.values())
    filas.append(["TOTAL", str(tn), mxn(tf), mxn(tu)])
    t = tabla(filas, [3.6*cm, 3.2*cm, 4.4*cm, 4.6*cm], alinea_der=(1,2,3))
    t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                           ("BACKGROUND", (0,-1), (-1,-1), AZUL_L)]))
    h.append(t)
    nm = len(M) or 1
    prom_ev, prom_fa = tn / nm, tf / nm
    margen = (tu / tf * 100) if tf else 0
    h.append(Spacer(1, 0.3 * cm))
    h.append(tarjetas([
        ("Eventos por mes", f"{prom_ev:.1f}", f"{nm} meses con registro", AZUL_L),
        ("Facturado por mes", mxn(prom_fa), "Promedio", AZUL_L),
        ("Margen capturado", f"{margen:.0f}%", "Utilidad ÷ facturado", AMBAR_L),
        ("Ocupación", f"{prom_ev/12*100:.0f}%", "Sobre 12 lugares de fin de semana", ROJO_L),
    ]))
    h.append(Spacer(1, 0.3 * cm))
    h.append(Paragraph(
        f"Celebra Sur promedia {prom_ev:.1f} eventos y {mxn(prom_fa)} facturados al mes. Es el "
        "único activo grande sin deuda y sin litigio. Bien rentado puede llegar a $200,000 "
        f"mensuales, que con el margen observado de {margen:.0f}% serían unos "
        f"{mxn(tf and 200000 * tu / tf)} de utilidad al mes.", E["cuerpo"]))
    h.append(Paragraph(
        "Cuidado al leer el margen: varios meses traen la utilidad en cero porque no se capturó, "
        "no porque el evento no dejara nada. El margen real puede ser más alto.", E["nota"]))


def sec_movimientos(h, d):
    h.append(Paragraph("6. Movimientos capturados en la app", E["seccion"]))

    if d["rentas"]:
        h.append(Paragraph("Rentas", E["sub2"]))
        filas = [["Propiedad", "Vence", "Monto", "Cobrada el", "Estatus"]]
        cob = atr = 0.0
        hoy = date.today().isoformat()
        for r in sorted(d["rentas"], key=lambda x: x.get("fecha_vencimiento") or ""):
            pagada = bool(r.get("fecha_ingreso_real"))
            venc = r.get("fecha_vencimiento") or ""
            est = "Pagada" if pagada else ("Atrasada" if venc and venc < hoy else "Pendiente")
            m = float(r.get("monto_renta") or 0)
            cob += m if pagada else 0
            atr += m if est == "Atrasada" else 0
            filas.append([r.get("propiedad") or "—", venc, mxn(m),
                          r.get("fecha_ingreso_real") or "—", est])
        h.append(tabla(filas, [4.4*cm, 2.8*cm, 2.8*cm, 3.0*cm, 2.8*cm], alinea_der=(2,)))
        tot = sum(float(r.get("monto_renta") or 0) for r in d["rentas"])
        h.append(tarjetas([("Registrado", mxn(tot), f"{len(d['rentas'])} períodos", AZUL_L),
                           ("Cobrado", mxn(cob), "Con pago recibido", VERDE_L),
                           ("Atrasado", mxn(atr), "Venció sin pago", ROJO_L)]))

    if d["autos_app"]:
        h.append(Paragraph("Autos", E["sub2"]))
        filas = [["Fecha", "Unidad", "Tipo", "Costo", "Utilidad"]]
        for r in sorted(d["autos_app"], key=lambda x: x.get("fecha") or "", reverse=True):
            filas.append([r.get("fecha") or "—", r.get("unidad") or "—", r.get("tipo") or "—",
                          mxn(r.get("costo")), mxn(r.get("utilidad"))])
        filas.append(["", "", "TOTAL", "",
                      mxn(sum(float(r.get("utilidad") or 0) for r in d["autos_app"]))])
        t = tabla(filas, [2.8*cm, 4.6*cm, 3.0*cm, 3.2*cm, 3.2*cm], alinea_der=(3, 4))
        t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                               ("BACKGROUND", (0,-1), (-1,-1), AZUL_L)]))
        h.append(t)

    if d["fact"]:
        h.append(Paragraph("Facturaciones", E["sub2"]))
        filas = [["Fecha", "Cliente", "Unidad", "Tipo", "Monto"]]
        for r in sorted(d["fact"], key=lambda x: x.get("fecha") or "", reverse=True):
            filas.append([r.get("fecha") or "—",
                          Paragraph(f'<font size=8.2>{r.get("cliente") or "—"}</font>', E["cuerpo"]),
                          Paragraph(f'<font size=8.2>{r.get("unidad") or "—"}</font>', E["cuerpo"]),
                          r.get("tipo") or "—", mxn(r.get("monto"))])
        filas.append(["", "", "", "TOTAL",
                      mxn(sum(float(r.get("monto") or 0) for r in d["fact"]))])
        t = tabla(filas, [2.8*cm, 4.2*cm, 4.0*cm, 3.0*cm, 2.8*cm], alinea_der=(4,))
        t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                               ("BACKGROUND", (0,-1), (-1,-1), AZUL_L)]))
        h.append(t)

    if d["gastos_app"]:
        h.append(Paragraph("Gastos", E["sub2"]))
        filas = [["Fecha", "Módulo", "Concepto", "Monto"]]
        for r in sorted(d["gastos_app"], key=lambda x: x.get("fecha") or "", reverse=True):
            filas.append([r.get("fecha") or "—", r.get("modulo") or "—",
                          Paragraph(f'<font size=8.2>{r.get("concepto") or "—"}</font>',
                                    E["cuerpo"]),
                          mxn(r.get("monto"))])
        filas.append(["", "", "TOTAL",
                      mxn(sum(float(r.get("monto") or 0) for r in d["gastos_app"]))])
        t = tabla(filas, [2.8*cm, 3.6*cm, 7.4*cm, 3.0*cm], alinea_der=(3,))
        t.setStyle(TableStyle([("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.2),
                               ("BACKGROUND", (0,-1), (-1,-1), AZUL_L)]))
        h.append(t)


def sec_atencion(h, d):
    p = d["patrimonio"]
    liq = sum(float(x["monto"]) for x in p if x["tipo"] == "Activo" and x.get("liquido"))
    caja = caja_por_anio(d)
    ult = caja[-1] if caja else None

    puntos = []
    if ult and ult["res_mes"] < 0:
        aire = liq / abs(ult["res_mes"])
        puntos.append(("Caja", f"Pérdida de {mxn(abs(ult['res_mes']))} al mes contra "
                       f"{mxn(liq)} líquidos: alrededor de {aire:.1f} meses de aire."))
    en_litigio = [x for x in p if "litigio" in (x.get("notas") or "").lower()]
    if en_litigio:
        s = sum(float(x["monto"]) for x in en_litigio)
        puntos.append(("Litigios", f"{len(en_litigio)} pasivos en litigio por {mxn(s)}. "
                       "Mientras dure el pleito esas propiedades no se pueden vender ni hipotecar."))
    veh = [x for x in p if x["tipo"] == "Activo"
           and x.get("categoria") in ("Vehiculos", "Inventario / negocio")]
    if veh:
        bruto = sum(float(x["monto"]) for x in veh)
        puntos.append(("Vehículos", f"{len(veh)} unidades por {mxn(bruto)} brutos entre carros "
                       "personales e inventario del lote parado. Se liquidan más rápido que un "
                       "inmueble y no quitan ingreso de renta."))
    ev = [e for e in d["eventos"] if (e.get("fecha_evento") or "")[:4].isdigit()]
    if ev:
        nm = len({(e["fecha_evento"] or "")[:7] for e in ev})
        puntos.append(("Celebra Sur", f"{len(ev)/max(nm,1):.1f} eventos al mes sobre unos 12 "
                       "lugares de fin de semana disponibles. Es el activo sin deuda ni litigio "
                       "con más espacio para crecer sin meter capital."))
    sin_util = [e for e in ev if not float(e.get("utilidad") or 0)]
    if sin_util:
        puntos.append(("Captura", f"{len(sin_util)} de {len(ev)} eventos no tienen utilidad "
                       "capturada, así que el margen real del jardín puede ser mejor que el "
                       "que sale en este reporte."))

    filas = [["Tema", "Qué dice el dato"]]
    for a, b in puntos:
        filas.append([a, Paragraph(f'<font size=8.2>{b}</font>', E["cuerpo"])])
    h.append(KeepTogether([Paragraph("7. Puntos de atención", E["seccion"]),
                           tabla(filas, [3.0*cm, 14.8*cm])]))
    h.append(Spacer(1, 0.4 * cm))
    h.append(Paragraph(
        "Este reporte es una lectura de los datos capturados, no una recomendación profesional. "
        "Con hipotecas en litigio de por medio, cualquier movimiento de inmuebles conviene "
        "revisarlo antes con un abogado, y las decisiones financieras con un contador.",
        E["nota"]))


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.2 * cm, "Control Financiero — resumen del dashboard")
    canvas.drawRightString(LETTER[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(BORDE)
    canvas.line(2 * cm, 1.5 * cm, LETTER[0] - 2 * cm, 1.5 * cm)
    canvas.restoreState()


def generar(salida=None):
    d = reunir()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.8*cm, bottomMargin=2*cm,
                            title="Control Financiero — resumen del dashboard",
                            author="Control Financiero")
    h = []
    portada(h, d)
    sec_patrimonio(h, d)
    h.append(PageBreak())
    sec_caja(h, d)
    sec_autos(h, d)
    sec_ingresos(h, d)
    sec_celebra(h, d)
    sec_movimientos(h, d)
    sec_atencion(h, d)
    doc.build(h, onFirstPage=pie, onLaterPages=pie)
    pdf = buf.getvalue()
    if salida:
        Path(salida).write_bytes(pdf)
        print(f"PDF generado: {salida}  ({len(pdf)/1024:.0f} KB)")
    return pdf


if __name__ == "__main__":
    generar(sys.argv[1] if len(sys.argv) > 1 else "resumen_dashboard.pdf")
