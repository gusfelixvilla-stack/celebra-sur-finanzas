import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import (
    init_db, USE_SUPABASE,
    log_accion, get_eventos, get_rentas, get_historial,
    save_evento, delete_evento, save_renta, delete_renta,
    get_autos, save_auto, delete_auto,
    get_facturaciones, save_facturacion, delete_facturacion,
)
from contract import generar_contrato

init_db()

st.set_page_config(
    page_title="Control Financiero",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS — tema claro con fondo diferente por módulo
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  /* ── Base global ── */
  .stApp, [data-testid="stAppViewContainer"] {
    background: #f1f5f9;
    color: #1e293b;
  }
  [data-testid="stHeader"] { background: #f1f5f9; }
  [data-testid="stSidebar"] { background: #e2e8f0; }

  /* ── Tabs ── */
  [data-baseweb="tab-list"] {
    background: #ffffff !important;
    border-radius: 12px;
    padding: 4px 6px;
    gap: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
  }
  [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    color: #64748b !important;
  }
  [aria-selected="true"][data-baseweb="tab"] {
    background: #0ea5e9 !important;
    color: #ffffff !important;
  }

  /* ── Fondo por módulo — colorea el panel completo del tab activo ── */
  .bg-dash    { background: #bae6fd; border-radius: 16px; padding: 24px; margin-top: 8px; }
  .bg-eventos { background: #bbf7d0; border-radius: 16px; padding: 24px; margin-top: 8px; }
  .bg-rentas  { background: #ddd6fe; border-radius: 16px; padding: 24px; margin-top: 8px; }
  .bg-hist    { background: #fef08a; border-radius: 16px; padding: 24px; margin-top: 8px; }

  /* ── Cards KPI ── */
  .card {
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 14px;
    border: 1px solid rgba(0,0,0,.08);
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }
  .card-green  { background:#f0fdf4; border-left: 4px solid #22c55e; }
  .card-blue   { background:#f0f9ff; border-left: 4px solid #0ea5e9; }
  .card-purple { background:#faf5ff; border-left: 4px solid #a855f7; }
  .card-orange { background:#fff7ed; border-left: 4px solid #f97316; }
  .card-yellow { background:#fefce8; border-left: 4px solid #eab308; }

  .kpi-value { font-size: 2rem; font-weight: 700; color: #0f172a; margin: 4px 0; }
  .kpi-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: .06em; }
  .kpi-sub   { font-size: 0.82rem; color: #94a3b8; margin-top: 4px; }

  /* ── Badges ── */
  .badge {
    display: inline-block; padding: 3px 11px;
    border-radius: 9999px; font-size: 0.75rem; font-weight: 600;
  }
  .badge-green  { background:#dcfce7; color:#166534; }
  .badge-yellow { background:#fef9c3; color:#854d0e; }
  .badge-red    { background:#fee2e2; color:#991b1b; }

  /* ── Banner de usuario ── */
  .user-banner {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 16px;
    display: flex; align-items: center; gap: 10px;
    font-size: 0.9rem; color: #334155;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
  }

  /* ── Inputs claros ── */
  input, textarea, select { color: #1e293b !important; }

  /* ── Tablas ── */
  .stDataFrame { border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.07); }
</style>
""", unsafe_allow_html=True)

PROPIEDADES = ["Casa San Carlos", "Casa Encinos 1", "Casa Encinos 3"]

# ══════════════════════════════════════════════════════════════════════════════
# Identificación de usuario (persiste en sesión)
# ══════════════════════════════════════════════════════════════════════════════
if "usuario" not in st.session_state:
    st.session_state.usuario = ""

with st.container():
    col_u, col_title = st.columns([1, 3])
    with col_u:
        nombre = st.text_input("👤 ¿Quién eres?", value=st.session_state.usuario,
                                placeholder="Tu nombre", key="_nombre_input",
                                label_visibility="collapsed")
        if nombre != st.session_state.usuario:
            st.session_state.usuario = nombre
    with col_title:
        st.markdown("# 💰 Control Financiero")

usuario_activo = st.session_state.usuario.strip() or "Anónimo"

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def fmt_mxn(n):
    if n is None: return "$0"
    return f"${n:,.0f}"


def estatus_renta(fecha_vencimiento: str, fecha_ingreso):
    if fecha_ingreso:
        return "Pagado"
    venc = date.fromisoformat(fecha_vencimiento)
    return "Atrasado" if date.today() > venc else "Pendiente"


def badge_html(estatus):
    cls = {"Pagado": "badge-green", "Al corriente": "badge-green",
           "Pendiente": "badge-yellow", "Atrasado": "badge-red",
           "Apartado": "badge-yellow", "Liquidado": "badge-green"}.get(estatus, "badge-yellow")
    return f'<span class="badge {cls}">{estatus}</span>'


def kpi(label, value, sub="", color="blue"):
    st.markdown(f"""
    <div class="card card-{color}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Data layer
# ══════════════════════════════════════════════════════════════════════════════

# Las funciones de datos viven en database.py (importadas arriba):
# log_accion, get_eventos, get_rentas, get_historial,
# save_evento, delete_evento, save_renta, delete_renta


# ══════════════════════════════════════════════════════════════════════════════
# Calendario de disponibilidad
# ══════════════════════════════════════════════════════════════════════════════

import calendar as _cal

MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
DIAS_ES  = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]


def render_calendario(anio: int, mes: int, fechas_ocupadas: dict) -> str:
    """
    Devuelve HTML de un calendario mensual.
    fechas_ocupadas: {date: concepto_str}
    """
    cal = _cal.monthcalendar(anio, mes)
    hoy = date.today()

    html = f"""
    <style>
      .cal-wrap {{ background:#ffffff; border-radius:14px; padding:16px 12px;
                   box-shadow:0 2px 8px rgba(0,0,0,.08); user-select:none; }}
      .cal-title {{ text-align:center; font-size:1.05rem; font-weight:700;
                    color:#1e40af; margin-bottom:10px; }}
      .cal-grid  {{ display:grid; grid-template-columns:repeat(7,1fr); gap:3px; }}
      .cal-head  {{ text-align:center; font-size:.72rem; font-weight:600;
                    color:#64748b; padding:4px 0; }}
      .cal-day   {{ text-align:center; border-radius:8px; padding:6px 2px;
                    font-size:.82rem; cursor:default; transition:.15s; }}
      .cal-empty {{ visibility:hidden; }}
      .cal-hoy   {{ background:#1e40af; color:#fff; font-weight:700; border-radius:50%;}}
      .cal-libre {{ background:#dcfce7; color:#166534; font-weight:600; }}
      .cal-ocup  {{ background:#fee2e2; color:#991b1b; font-weight:700;
                    cursor:pointer; border-radius:8px; }}
      .cal-ocup:hover {{ background:#fca5a5; }}
      .cal-pas   {{ color:#cbd5e1; }}
      .cal-legend {{ display:flex; gap:12px; justify-content:center;
                     margin-top:10px; font-size:.75rem; color:#475569; }}
      .dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; margin-right:4px; }}
    </style>
    <div class="cal-wrap">
      <div class="cal-title">📅 {MESES_ES[mes-1]} {anio}</div>
      <div class="cal-grid">
    """
    for d in DIAS_ES:
        html += f'<div class="cal-head">{d}</div>'

    for semana in cal:
        for dia in semana:
            if dia == 0:
                html += '<div class="cal-day cal-empty">·</div>'
                continue
            d = date(anio, mes, dia)
            if d in fechas_ocupadas:
                tip = fechas_ocupadas[d]
                html += f'<div class="cal-day cal-ocup" title="{tip}">🔴{dia}</div>'
            elif d == hoy:
                html += f'<div class="cal-day cal-hoy">{dia}</div>'
            elif d < hoy:
                html += f'<div class="cal-day cal-pas">{dia}</div>'
            else:
                html += f'<div class="cal-day cal-libre">{dia}</div>'

    html += """
      </div>
      <div class="cal-legend">
        <span><span class="dot" style="background:#4ade80"></span>Disponible</span>
        <span><span class="dot" style="background:#f87171"></span>Ocupado</span>
        <span><span class="dot" style="background:#1e40af"></span>Hoy</span>
      </div>
    </div>
    """
    return html


def render_calendario_renta(anio: int, mes: int, rangos_ocupados: list, propiedad: str) -> str:
    """
    Calendaio para una propiedad.
    rangos_ocupados: lista de (fecha_inicio, fecha_fin, notas)
    """
    cal = _cal.monthcalendar(anio, mes)
    hoy = date.today()

    COLORES = {
        "Casa San Carlos": ("#0ea5e9", "#e0f2fe", "#0369a1"),
        "Casa Encinos 1":  ("#22c55e", "#dcfce7", "#15803d"),
        "Casa Encinos 3":  ("#a855f7", "#f3e8ff", "#7e22ce"),
    }
    c_acento, c_fondo, c_oscuro = COLORES.get(propiedad, ("#64748b","#f1f5f9","#334155"))

    # Construir set de fechas ocupadas con su info
    ocupadas = {}
    for fi, ff, nota in rangos_ocupados:
        try:
            d_ini = date.fromisoformat(fi) if fi else None
            d_fin = date.fromisoformat(ff)
            cursor = d_ini or d_fin
            end    = d_fin
            while cursor <= end:
                ocupadas[cursor] = nota or "Ocupado"
                cursor += timedelta(days=1)
        except Exception:
            pass

    html = f"""
    <style>
      .rcal-{mes} {{ background:#ffffff; border-radius:14px; padding:14px 10px;
                     box-shadow:0 2px 8px rgba(0,0,0,.08); margin-bottom:8px; }}
      .rcal-title-{mes} {{ text-align:center; font-size:.95rem; font-weight:700;
                           color:{c_oscuro}; margin-bottom:8px; }}
      .rcal-grid-{mes} {{ display:grid; grid-template-columns:repeat(7,1fr); gap:3px; }}
      .rcal-head-{mes} {{ text-align:center; font-size:.7rem; font-weight:600;
                          color:#64748b; padding:3px 0; }}
      .rcal-day-{mes} {{ text-align:center; border-radius:7px; padding:5px 2px;
                         font-size:.8rem; }}
      .rcal-libre-{mes} {{ background:{c_fondo}; color:{c_oscuro}; font-weight:600; }}
      .rcal-ocup-{mes}  {{ background:{c_acento}; color:#fff; font-weight:700;
                           border-radius:7px; cursor:default; }}
      .rcal-hoy-{mes}   {{ background:#1e40af; color:#fff; font-weight:700; border-radius:50%;}}
      .rcal-pas-{mes}   {{ color:#cbd5e1; }}
      .rcal-vacio-{mes} {{ visibility:hidden; }}
      .rcal-legend-{mes} {{ display:flex; gap:10px; justify-content:center;
                            margin-top:8px; font-size:.72rem; color:#475569; }}
      .rdot {{ width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:3px; }}
    </style>
    <div class="rcal-{mes}">
      <div class="rcal-title-{mes}">📅 {MESES_ES[mes-1]} {anio}</div>
      <div class="rcal-grid-{mes}">
    """
    for d in DIAS_ES:
        html += f'<div class="rcal-head-{mes}">{d}</div>'

    for semana in cal:
        for dia in semana:
            if dia == 0:
                html += f'<div class="rcal-day-{mes} rcal-vacio-{mes}">·</div>'
                continue
            d = date(anio, mes, dia)
            if d in ocupadas:
                html += f'<div class="rcal-day-{mes} rcal-ocup-{mes}" title="{ocupadas[d]}">🔴{dia}</div>'
            elif d == hoy:
                html += f'<div class="rcal-day-{mes} rcal-hoy-{mes}">{dia}</div>'
            elif d < hoy:
                html += f'<div class="rcal-day-{mes} rcal-pas-{mes}">{dia}</div>'
            else:
                html += f'<div class="rcal-day-{mes} rcal-libre-{mes}">{dia}</div>'

    html += f"""
      </div>
      <div class="rcal-legend-{mes}">
        <span><span class="rdot" style="background:{c_acento}"></span>Ocupado</span>
        <span><span class="rdot" style="background:{c_fondo};border:1px solid {c_acento}"></span>Disponible</span>
        <span><span class="rdot" style="background:#1e40af"></span>Hoy</span>
      </div>
    </div>
    """
    return html


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard helpers
# ══════════════════════════════════════════════════════════════════════════════

def ingresos_del_dia(dia: date):
    dia_str = dia.strftime("%Y-%m-%d")
    detalle_eventos, detalle_rentas = [], []
    total_eventos = total_rentas = 0

    for e in get_eventos():
        aporte, desc = 0, []
        if e["fecha_apartado"] == dia_str and e["monto_apartado"]:
            aporte += e["monto_apartado"]
            desc.append(f"Apartado {fmt_mxn(e['monto_apartado'])}")
        saldo = e["costo_total"] - e["monto_apartado"]
        if e["fecha_liquidacion"] == dia_str and e["estatus"] == "Liquidado":
            aporte += saldo
            desc.append(f"Liquidación {fmt_mxn(saldo)}")
        if aporte > 0:
            total_eventos += aporte
            detalle_eventos.append({"Cliente": e["concepto"], "Detalle": ", ".join(desc), "Monto": aporte})

    for r in get_rentas():
        if r["fecha_ingreso_real"] == dia_str:
            total_rentas += r["monto_renta"]
            detalle_rentas.append({"Propiedad": r["propiedad"], "Vencimiento": r["fecha_vencimiento"], "Monto": r["monto_renta"]})

    return total_eventos + total_rentas, total_eventos, total_rentas, detalle_eventos, detalle_rentas


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_dash, tab_eventos, tab_rentas, tab_autos, tab_fact, tab_hist = st.tabs(
    ["📊 Dashboard", "🎉 Eventos", "🏠 Rentas", "🚗 Autos", "🧾 Facturaciones", "📋 Historial"]
)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DASHBOARD  (fondo azul cielo)
# ─────────────────────────────────────────────────────────────────────────────
with tab_dash:
    st.markdown('<div class="bg-dash">', unsafe_allow_html=True)

    # ── KPIs globales siempre visibles ────────────────────────────────────────
    todos_ev   = get_eventos()
    todas_rent = get_rentas()

    total_pactado  = sum(e["costo_total"] for e in todos_ev)
    total_cobrado  = sum(
        e["monto_apartado"] + (e["costo_total"] - e["monto_apartado"]
        if e["estatus"] == "Liquidado" else 0)
        for e in todos_ev
    )
    total_pendiente_ev = total_pactado - total_cobrado
    total_util = sum(e.get("utilidad", 0) for e in todos_ev)

    rent_cobradas  = sum(r["monto_renta"] for r in todas_rent if r["fecha_ingreso_real"])
    rent_pendiente = sum(
        r["monto_renta"] for r in todas_rent
        if not r["fecha_ingreso_real"]
    )

    st.markdown("### 📊 Resumen General")
    g1, g2, g3, g4 = st.columns(4)
    with g1: kpi("Eventos pactados", fmt_mxn(total_pactado), f"{len(todos_ev)} eventos", "blue")
    with g2: kpi("Cobrado eventos", fmt_mxn(total_cobrado), "Apartados + liquidados", "green")
    with g3: kpi("Rentas cobradas", fmt_mxn(rent_cobradas), f"{sum(1 for r in todas_rent if r['fecha_ingreso_real'])} pagos", "purple")
    with g4: kpi("Utilidades totales", fmt_mxn(total_util), "Ganancia neta eventos", "orange")

    st.markdown("---")

    # ── Próximos eventos ──────────────────────────────────────────────────────
    hoy = date.today()
    proximos = sorted(
        [e for e in todos_ev if e["fecha_evento"] >= hoy.isoformat()],
        key=lambda e: e["fecha_evento"]
    )
    atrasados = sorted(
        [e for e in todos_ev if e["fecha_evento"] < hoy.isoformat() and e["estatus"] == "Apartado"],
        key=lambda e: e["fecha_evento"], reverse=True
    )

    col_ev, col_rent = st.columns(2)

    with col_ev:
        st.markdown("#### 🎉 Eventos registrados")
        if proximos:
            st.markdown("**Próximos:**")
            for e in proximos[:8]:
                dias = (date.fromisoformat(e["fecha_evento"]) - hoy).days
                tag = "🟢 Hoy" if dias == 0 else (f"📅 En {dias}d" if dias > 0 else f"⚠️ Hace {-dias}d")
                est_color = "🟡" if e["estatus"] == "Apartado" else "✅"
                saldo = e["costo_total"] - e["monto_apartado"]
                st.markdown(
                    f"""<div class="card card-blue" style="padding:10px 14px;margin-bottom:8px;">
                    <b>{e['fecha_evento']}</b> {tag}<br>
                    👤 {e['concepto']}<br>
                    💰 {fmt_mxn(e['costo_total'])} {est_color} {e['estatus']}
                    {"— Saldo: <b>" + fmt_mxn(saldo) + "</b>" if saldo > 0 else " ✅ Liquidado"}
                    </div>""", unsafe_allow_html=True
                )
        if atrasados:
            st.markdown("**⚠️ Pendientes de liquidar (fecha ya pasó):**")
            for e in atrasados[:4]:
                saldo = e["costo_total"] - e["monto_apartado"]
                st.markdown(
                    f"""<div class="card card-orange" style="padding:10px 14px;margin-bottom:8px;">
                    <b>{e['fecha_evento']}</b> — {e['concepto']}<br>
                    Saldo por cobrar: <b>{fmt_mxn(saldo)}</b>
                    </div>""", unsafe_allow_html=True
                )
        if not proximos and not atrasados:
            st.info("No hay eventos registrados aún.")

    with col_rent:
        st.markdown("#### 🏠 Rentas registradas")
        if todas_rent:
            rent_ord = sorted(todas_rent, key=lambda r: r["fecha_vencimiento"])
            for r in rent_ord[:10]:
                est = estatus_renta(r["fecha_vencimiento"], r["fecha_ingreso_real"])
                color = {"Pagado": "green", "Pendiente": "blue", "Atrasado": "orange"}.get(est, "blue")
                icono = {"Pagado": "✅", "Pendiente": "🕐", "Atrasado": "🔴"}.get(est, "🕐")
                st.markdown(
                    f"""<div class="card card-{color}" style="padding:10px 14px;margin-bottom:8px;">
                    <b>{r['propiedad']}</b> {icono} {est}<br>
                    Vence: {r['fecha_vencimiento']} — <b>{fmt_mxn(r['monto_renta'])}</b>
                    {"<br>Pagado: " + r['fecha_ingreso_real'] if r['fecha_ingreso_real'] else ""}
                    </div>""", unsafe_allow_html=True
                )
        else:
            st.info("No hay rentas registradas aún.")

    st.markdown("---")

    # ── Dinero del día (filtro por fecha) ─────────────────────────────────────
    st.markdown("### 📅 ¿Cuánto dinero cayó en un día?")
    col_f, _ = st.columns([1, 3])
    with col_f:
        dia_sel = st.date_input("Día", value=date.today(), key="dash_fecha", label_visibility="collapsed")

    total, tot_ev, tot_rent, det_ev, det_rent = ingresos_del_dia(dia_sel)

    c1, c2, c3 = st.columns(3)
    with c1: kpi("Total del día", fmt_mxn(total), dia_sel.strftime("%d/%m/%Y"), "green")
    with c2: kpi("De eventos", fmt_mxn(tot_ev), f"{len(det_ev)} movimiento(s)", "blue")
    with c3: kpi("De rentas", fmt_mxn(tot_rent), f"{len(det_rent)} propiedad(es)", "purple")

    if det_ev:
        st.markdown("##### Desglose Eventos")
        df = pd.DataFrame(det_ev); df["Monto"] = df["Monto"].apply(fmt_mxn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    if det_rent:
        st.markdown("##### Desglose Rentas")
        df = pd.DataFrame(det_rent); df["Monto"] = df["Monto"].apply(fmt_mxn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    if not det_ev and not det_rent:
        st.info("Sin ingresos en esa fecha.")

    st.markdown("---")
    st.markdown("##### Últimos 7 días")
    resumen = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        t, te, tr, _, _ = ingresos_del_dia(d)
        resumen.append({"Fecha": d.strftime("%d/%m"), "Eventos": te, "Rentas": tr})
    st.bar_chart(pd.DataFrame(resumen).set_index("Fecha"))
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — EVENTOS  (fondo verde clarito)
# ─────────────────────────────────────────────────────────────────────────────
with tab_eventos:
    st.markdown('<div class="bg-eventos">', unsafe_allow_html=True)
    st.markdown("### 🎉 Local de Eventos")

    # ── Calendario de disponibilidad ──────────────────────────────────────────
    eventos_todos = get_eventos()
    fechas_ocupadas = {}
    for e in eventos_todos:
        try:
            fechas_ocupadas[date.fromisoformat(e["fecha_evento"])] = e["concepto"]
        except Exception:
            pass

    # Navegación de mes
    if "cal_anio" not in st.session_state:
        st.session_state.cal_anio = date.today().year
    if "cal_mes" not in st.session_state:
        st.session_state.cal_mes = date.today().month
    if "fecha_presel" not in st.session_state:
        st.session_state.fecha_presel = None

    col_prev, col_mes_label, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("◀", key="cal_prev"):
            if st.session_state.cal_mes == 1:
                st.session_state.cal_mes = 12
                st.session_state.cal_anio -= 1
            else:
                st.session_state.cal_mes -= 1
    with col_mes_label:
        st.markdown(
            f"<div style='text-align:center;font-weight:600;color:#1e40af;font-size:1rem;padding-top:6px'>"
            f"{MESES_ES[st.session_state.cal_mes-1]} {st.session_state.cal_anio}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("▶", key="cal_next"):
            if st.session_state.cal_mes == 12:
                st.session_state.cal_mes = 1
                st.session_state.cal_anio += 1
            else:
                st.session_state.cal_mes += 1

    cal_html = render_calendario(
        st.session_state.cal_anio, st.session_state.cal_mes, fechas_ocupadas
    )
    st.markdown(cal_html, unsafe_allow_html=True)

    # Eventos del mes visualizado
    mes_str = f"{st.session_state.cal_anio}-{st.session_state.cal_mes:02d}"
    ev_mes = [e for e in eventos_todos if e["fecha_evento"].startswith(mes_str)]
    if ev_mes:
        st.markdown(f"**Eventos en {MESES_ES[st.session_state.cal_mes-1]}:** " +
                    " · ".join([f"🔴 {e['fecha_evento'][8:10]} {e['concepto']}" for e in ev_mes]))

    st.markdown("---")

    # ── Formulario ────────────────────────────────────────────────────────────
    with st.expander("➕ Registrar / Editar Evento", expanded=False):
        eventos_lista = get_eventos()
        opciones = ["Nuevo Evento"] + [f"#{e['id']} – {e['concepto']} ({e['fecha_evento']})" for e in eventos_lista]
        sel = st.selectbox("Seleccionar", opciones, key="ev_sel")

        ev, edit_id = {}, None
        if sel != "Nuevo Evento":
            edit_id = int(sel.split("–")[0].replace("#", "").strip())
            ev = next(e for e in eventos_lista if e["id"] == edit_id)

        # Si viene fecha preseleccionada del calendario
        fecha_default = date.today()
        if st.session_state.get("fecha_presel"):
            fecha_default = st.session_state.fecha_presel
        if ev.get("fecha_evento"):
            fecha_default = date.fromisoformat(ev["fecha_evento"])

        c1, c2 = st.columns(2)
        with c1:
            fecha_evento = st.date_input("Fecha del Evento", value=fecha_default, key="ev_fe")
            concepto = st.text_input("Concepto / Cliente", value=ev.get("concepto", ""), key="ev_con")
            costo_total = st.number_input("Costo Total ($)", min_value=0.0, step=500.0,
                value=float(ev.get("costo_total", 0)), key="ev_ct")
            utilidad_monto = st.number_input("Utilidad neta ($)", min_value=0.0, step=100.0,
                value=float(ev.get("utilidad", 0)), key="ev_util",
                help="Ganancia neta que te quedas de este evento")
        with c2:
            monto_ap = st.number_input("Monto Apartado ($)", min_value=0.0, step=500.0,
                value=float(ev.get("monto_apartado", 0)), key="ev_ma")
            fecha_ap = st.date_input("Fecha de Apartado",
                value=date.fromisoformat(ev["fecha_apartado"]) if ev.get("fecha_apartado") else date.today(),
                key="ev_fa")
            estatus = st.selectbox("Estatus", ["Apartado", "Liquidado"],
                index=["Apartado","Liquidado"].index(ev.get("estatus","Apartado")), key="ev_es")
            fecha_liq = None
            if estatus == "Liquidado":
                fecha_liq = st.date_input("Fecha de Liquidación",
                    value=date.fromisoformat(ev["fecha_liquidacion"]) if ev.get("fecha_liquidacion") else date.today(),
                    key="ev_fl")

        saldo = max(0.0, costo_total - monto_ap)
        pct_display = (utilidad_monto / costo_total * 100) if costo_total > 0 else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Saldo Pendiente", fmt_mxn(saldo))
        m2.metric("Utilidad neta", fmt_mxn(utilidad_monto))
        m3.metric("% sobre costo", f"{pct_display:.1f}%")

        cs, cd = st.columns([3, 1])
        with cs:
            if st.button("💾 Guardar Evento", use_container_width=True, key="ev_save"):
                if not concepto:
                    st.error("El concepto/cliente es obligatorio.")
                else:
                    payload = {
                        "fecha_evento": fecha_evento.isoformat(), "concepto": concepto,
                        "costo_total": costo_total, "monto_apartado": monto_ap,
                        "fecha_apartado": fecha_ap.isoformat(), "estatus": estatus,
                        "fecha_liquidacion": fecha_liq.isoformat() if fecha_liq else None,
                        "utilidad": utilidad_monto,
                    }
                    save_evento(payload, edit_id)
                    st.session_state.fecha_presel = None
                    accion = "Editó evento" if edit_id else "Creó evento"
                    log_accion(usuario_activo, accion, "Eventos", f"{concepto} — {fmt_mxn(costo_total)}")
                    st.success("Evento guardado ✓")
                    st.rerun()
        with cd:
            if edit_id and st.button("🗑️ Eliminar", use_container_width=True, key="ev_del"):
                log_accion(usuario_activo, "Eliminó evento", "Eventos",
                           f"#{edit_id} {ev.get('concepto')} — {fmt_mxn(ev.get('costo_total',0))}")
                delete_evento(edit_id)
                st.warning("Evento eliminado.")
                st.rerun()

    # ── Tabla resumen ─────────────────────────────────────────────────────────
    eventos = get_eventos()
    if eventos:
        rows = []
        for e in eventos:
            rows.append({
                "Fecha": e["fecha_evento"], "Cliente": e["concepto"],
                "Costo": fmt_mxn(e["costo_total"]), "Apartado": fmt_mxn(e["monto_apartado"]),
                "Saldo": fmt_mxn(e["costo_total"] - e["monto_apartado"]),
                "Estatus": e["estatus"],
                "Utilidad": fmt_mxn(e.get("utilidad", 0)),
                "F. Liq.": e["fecha_liquidacion"] or "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        total_p = sum(e["costo_total"] for e in eventos)
        total_c = sum(e["monto_apartado"] + (e["costo_total"]-e["monto_apartado"] if e["estatus"]=="Liquidado" else 0) for e in eventos)
        total_u = sum(e.get("utilidad", 0) for e in eventos)
        k1, k2, k3 = st.columns(3)
        with k1: kpi("Total Pactado", fmt_mxn(total_p), "Todos los eventos", "blue")
        with k2: kpi("Total Cobrado", fmt_mxn(total_c), "Apartados + Liquidados", "green")
        with k3: kpi("Utilidades Totales", fmt_mxn(total_u), "Suma de utilidades netas", "orange")
    else:
        st.info("No hay eventos registrados aún.")

    # ── Generador de Contrato ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📄 Generar Contrato en PDF")

    eventos_para_contrato = get_eventos()
    if not eventos_para_contrato:
        st.info("Primero registra un evento para generar su contrato.")
    else:
        with st.expander("📝 Configurar y descargar contrato", expanded=False):
            opciones_cont = [f"#{e['id']} – {e['concepto']} ({e['fecha_evento']})" for e in eventos_para_contrato]
            sel_cont = st.selectbox("Evento para el contrato", opciones_cont, key="cont_sel")
            ev_cont = next(e for e in eventos_para_contrato
                           if e["id"] == int(sel_cont.split("–")[0].replace("#","").strip()))

            st.markdown("##### Datos del negocio y del arrendatario")
            c1, c2 = st.columns(2)
            with c1:
                nombre_negocio = st.text_input("Nombre del salón / negocio",
                    value="Celebra Sur", key="cont_neg")
                salon = st.text_input("Dirección del salón",
                    value="Hermosillo, Sonora", key="cont_salon")
                representante = st.text_input("Representante legal del salón",
                    value="", placeholder="Nombre del propietario o representante", key="cont_rep")
            with c2:
                arrendatario = st.text_input(
                    "✍️ Nombre completo de quien renta (aparecerá en la firma)",
                    value="",
                    placeholder="Ej. Juan Carlos Pérez Rodríguez",
                    key="cont_arrendatario",
                    help="Este nombre saldrá al final del contrato para que la persona firme",
                )
                if arrendatario:
                    st.markdown(
                        f"<div style='background:#dcfce7;border-radius:8px;padding:8px 12px;"
                        f"font-size:.85rem;color:#166534;margin-top:4px'>"
                        f"✅ Firmará como: <b>{arrendatario}</b></div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("##### Detalles del evento")
            c1, c2 = st.columns(2)
            with c1:
                hora_inicio = st.text_input("Hora de inicio", value="18:00", key="cont_hora")
                horas_servicio = st.number_input("Duración (horas)", min_value=1, max_value=24,
                    value=5, key="cont_horas")
                alcohol = st.selectbox("Política de alcohol",
                    ["Sin alcohol", "Con alcohol — bajo responsabilidad del arrendatario",
                     "Bebidas de cortesía incluidas (sin licor)"],
                    key="cont_alc")
            with c2:
                fecha_lim_pago = st.date_input("Fecha límite para liquidar saldo",
                    value=date.fromisoformat(ev_cont["fecha_evento"]) if ev_cont.get("fecha_evento") else date.today(),
                    key="cont_flim")
                folio = st.text_input("Folio", value=f"CS-{ev_cont['id']:04d}", key="cont_folio")
                tipo_evento = st.text_input("Tipo de evento",
                    value="", placeholder="Ej. XV Años, Boda, Graduación, Cumpleaños...",
                    key="cont_tipo")

            st.markdown("##### Cláusulas adicionales personalizadas")
            st.caption("Escribe condiciones especiales para este evento. Deja en blanco las que no necesites.")
            clausulas_extra = []
            for i in range(1, 6):
                cl = st.text_area(f"Cláusula extra {i}", value="", height=55,
                    key=f"cont_cl{i}", label_visibility="collapsed",
                    placeholder=f"Cláusula adicional {i} — escribe aquí o deja en blanco")
                clausulas_extra.append(cl)

            saldo_cont = ev_cont["costo_total"] - ev_cont["monto_apartado"]
            st.markdown("##### Vista previa del contrato")
            prev_data = {
                "Salón": nombre_negocio, "Arrendatario": arrendatario,
                "Fecha evento": ev_cont["fecha_evento"],
                "Tipo": tipo_evento or ev_cont["concepto"],
                "Costo total": fmt_mxn(ev_cont["costo_total"]),
                "Apartado": fmt_mxn(ev_cont["monto_apartado"]),
                "Saldo": fmt_mxn(saldo_cont),
                "Horario": f"{hora_inicio} · {horas_servicio}h",
                "Alcohol": alcohol,
            }
            st.dataframe(pd.DataFrame([prev_data]).T.rename(columns={0: "Valor"}),
                         use_container_width=True)

            if st.button("⬇️ Generar y Descargar Contrato PDF", use_container_width=True,
                          type="primary", key="cont_gen"):
                try:
                    pdf_bytes = generar_contrato(
                        nombre_negocio=nombre_negocio or "Celebra Sur",
                        representante=representante or nombre_negocio,
                        arrendatario=arrendatario or ev_cont["concepto"],
                        tipo_evento=tipo_evento or ev_cont["concepto"],
                        fecha_evento=ev_cont["fecha_evento"],
                        hora_inicio=hora_inicio,
                        horas_servicio=int(horas_servicio),
                        costo_total=ev_cont["costo_total"],
                        monto_apartado=ev_cont["monto_apartado"],
                        fecha_apartado=ev_cont.get("fecha_apartado",""),
                        saldo_pendiente=saldo_cont,
                        fecha_limite_pago=fecha_lim_pago.strftime("%d/%m/%Y"),
                        salon=salon or "Hermosillo, Sonora",
                        alcohol=alcohol,
                        clausulas_extra=[c for c in clausulas_extra if c.strip()],
                        folio=folio,
                    )
                    nombre_archivo = f"Contrato_{arrendatario.replace(' ','_') or ev_cont['concepto'].replace(' ','_')}_{ev_cont['fecha_evento']}.pdf"
                    st.download_button(
                        label="📥 Haz clic aquí para descargar el PDF",
                        data=pdf_bytes,
                        file_name=nombre_archivo,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    log_accion(usuario_activo, "Generó contrato PDF", "Eventos",
                               f"{arrendatario or ev_cont['concepto']} — {ev_cont['fecha_evento']}")
                    st.success(f"✅ Contrato generado: {nombre_archivo}")
                except Exception as ex:
                    st.error(f"Error al generar el PDF: {ex}")

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — RENTAS  (fondo morado lavanda)
# ─────────────────────────────────────────────────────────────────────────────
with tab_rentas:
    st.markdown('<div class="bg-rentas">', unsafe_allow_html=True)
    st.markdown("### 🏠 Control de Rentas")

    todas_rentas = get_rentas()

    # ── Calendarios por propiedad ────────────────────────────────────────────
    ICONOS_PROP = {
        "Casa San Carlos": "🏡",
        "Casa Encinos 1":  "🏠",
        "Casa Encinos 3":  "🏘️",
    }

    # Navegación de mes (compartida para las 3 casas)
    if "rcal_anio" not in st.session_state:
        st.session_state.rcal_anio = date.today().year
    if "rcal_mes" not in st.session_state:
        st.session_state.rcal_mes = date.today().month

    col_rp, col_rm, col_rn = st.columns([1, 4, 1])
    with col_rp:
        if st.button("◀", key="rcal_prev"):
            if st.session_state.rcal_mes == 1:
                st.session_state.rcal_mes = 12; st.session_state.rcal_anio -= 1
            else:
                st.session_state.rcal_mes -= 1
    with col_rm:
        st.markdown(
            f"<div style='text-align:center;font-weight:700;color:#7e22ce;"
            f"font-size:1.05rem;padding-top:6px'>"
            f"{MESES_ES[st.session_state.rcal_mes-1]} {st.session_state.rcal_anio}</div>",
            unsafe_allow_html=True)
    with col_rn:
        if st.button("▶", key="rcal_next"):
            if st.session_state.rcal_mes == 12:
                st.session_state.rcal_mes = 1; st.session_state.rcal_anio += 1
            else:
                st.session_state.rcal_mes += 1

    # Mostrar 3 calendarios lado a lado
    cols_cal = st.columns(3)
    for idx, prop in enumerate(PROPIEDADES):
        rangos = [
            (r.get("fecha_inicio"), r["fecha_vencimiento"], r.get("notas",""))
            for r in todas_rentas if r["propiedad"] == prop
        ]
        html_cal = render_calendario_renta(
            st.session_state.rcal_anio, st.session_state.rcal_mes, rangos, prop
        )
        with cols_cal[idx]:
            st.markdown(f"**{ICONOS_PROP[prop]} {prop}**")
            st.markdown(html_cal, unsafe_allow_html=True)
            # Resumen rápido de esta propiedad
            rentas_prop = [r for r in todas_rentas if r["propiedad"] == prop]
            if rentas_prop:
                ultimo = sorted(rentas_prop, key=lambda r: r["fecha_vencimiento"], reverse=True)[0]
                est = estatus_renta(ultimo["fecha_vencimiento"], ultimo["fecha_ingreso_real"])
                st.markdown(badge_html(est), unsafe_allow_html=True)
            else:
                st.caption("Sin registros")

    st.markdown("---")

    # ── Formulario ────────────────────────────────────────────────────────────
    with st.expander("➕ Registrar / Editar Renta", expanded=False):
        rentas_lista = get_rentas()
        opciones_r = ["Nueva Renta"] + [
            f"#{r['id']} – {r['propiedad']} ({r.get('fecha_inicio','?')} → {r['fecha_vencimiento']})"
            for r in rentas_lista
        ]
        sel_r = st.selectbox("Seleccionar registro", opciones_r, key="r_sel")

        r, rent_id = {}, None
        if sel_r != "Nueva Renta":
            rent_id = int(sel_r.split("–")[0].replace("#", "").strip())
            r = next(x for x in rentas_lista if x["id"] == rent_id)

        c1, c2 = st.columns(2)
        with c1:
            propiedad = st.selectbox("Propiedad", PROPIEDADES,
                index=PROPIEDADES.index(r["propiedad"]) if r.get("propiedad") else 0,
                key="r_prop")
            fecha_ini = st.date_input("Fecha de Inicio de la Renta",
                value=date.fromisoformat(r["fecha_inicio"]) if r.get("fecha_inicio") else date.today(),
                key="r_ini")
            fecha_venc = st.date_input("Fecha de Vencimiento / Fin",
                value=date.fromisoformat(r["fecha_vencimiento"]) if r.get("fecha_vencimiento") else date.today(),
                key="r_venc")
        with c2:
            monto_renta = st.number_input("Monto de Renta ($)", min_value=0.0, step=100.0,
                value=float(r.get("monto_renta", 0)), key="r_monto")
            fecha_ing = st.date_input("Fecha de Pago Recibido",
                value=date.fromisoformat(r["fecha_ingreso_real"]) if r.get("fecha_ingreso_real") else None,
                key="r_fing")
            notas = st.text_input("Notas", value=r.get("notas") or "", key="r_notas")

        est = estatus_renta(fecha_venc.isoformat(), fecha_ing.isoformat() if fecha_ing else None)
        dias_renta = (fecha_venc - fecha_ini).days + 1 if fecha_venc >= fecha_ini else 0
        st.markdown(
            f"Estatus: {badge_html(est)} &nbsp;·&nbsp; "
            f"<span style='font-size:.85rem;color:#475569'>Período: <b>{dias_renta} días</b> "
            f"({fecha_ini.strftime('%d/%m')} al {fecha_venc.strftime('%d/%m/%Y')})</span>",
            unsafe_allow_html=True
        )

        cs2, cd2 = st.columns([3, 1])
        with cs2:
            if st.button("💾 Guardar Renta", use_container_width=True, key="r_save"):
                payload = {
                    "propiedad": propiedad,
                    "fecha_inicio": fecha_ini.isoformat(),
                    "fecha_vencimiento": fecha_venc.isoformat(),
                    "monto_renta": monto_renta,
                    "fecha_ingreso_real": fecha_ing.isoformat() if fecha_ing else None,
                    "notas": notas or None,
                }
                save_renta(payload, rent_id)
                accion = "Editó renta" if rent_id else "Creó renta"
                log_accion(usuario_activo, accion, "Rentas",
                           f"{propiedad} {fecha_ini}→{fecha_venc} — {fmt_mxn(monto_renta)}")
                st.success("Renta guardada ✓")
                st.rerun()
        with cd2:
            if rent_id and st.button("🗑️ Eliminar", use_container_width=True, key="r_del"):
                log_accion(usuario_activo, "Eliminó renta", "Rentas",
                           f"#{rent_id} {r.get('propiedad')} {r.get('fecha_vencimiento')}")
                delete_renta(rent_id)
                st.warning("Eliminado.")
                st.rerun()

    # ── Tabla y KPIs ──────────────────────────────────────────────────────────
    rentas = get_rentas()
    if rentas:
        def color_est(val):
            return {"Pagado":"color:#166534","Pendiente":"color:#854d0e","Atrasado":"color:#991b1b"}.get(val,"")

        rows_r = [{
            "Propiedad": r["propiedad"],
            "Inicio": r.get("fecha_inicio") or "—",
            "Vencimiento": r["fecha_vencimiento"],
            "Monto": fmt_mxn(r["monto_renta"]),
            "F. Pago": r["fecha_ingreso_real"] or "—",
            "Notas": r.get("notas") or "",
            "Estatus": estatus_renta(r["fecha_vencimiento"], r["fecha_ingreso_real"]),
        } for r in rentas]
        df_r = pd.DataFrame(rows_r)
        st.dataframe(df_r.style.map(color_est, subset=["Estatus"]), use_container_width=True, hide_index=True)

        total_r  = sum(r["monto_renta"] for r in rentas)
        cobradas = sum(r["monto_renta"] for r in rentas if r["fecha_ingreso_real"])
        atrasadas= sum(r["monto_renta"] for r in rentas
                       if not r["fecha_ingreso_real"] and estatus_renta(r["fecha_vencimiento"], None)=="Atrasado")
        k1, k2, k3 = st.columns(3)
        with k1: kpi("Total Registrado", fmt_mxn(total_r), f"{len(rentas)} períodos", "purple")
        with k2: kpi("Cobrado", fmt_mxn(cobradas), "Con pago recibido", "green")
        with k3: kpi("Atrasado", fmt_mxn(atrasadas), "Venció sin pago", "orange")
    else:
        st.info("No hay rentas registradas aún.")
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — AUTOS
# ─────────────────────────────────────────────────────────────────────────────
with tab_autos:
    st.markdown('<div class="bg-rentas">', unsafe_allow_html=True)
    st.markdown("## 🚗 Utilidad por Venta de Autos")

    # ── Formulario ────────────────────────────────────────────────────────────
    with st.expander("➕ Registrar / Editar Venta", expanded=False):
        autos_lista = get_autos()
        opciones_a = ["Nueva Venta"] + [
            f"#{a['id']} – {a['unidad']} ({a['fecha']})"
            for a in autos_lista
        ]
        sel_a = st.selectbox("Seleccionar registro", opciones_a, key="a_sel")
        auto_id = None
        a = {}
        if sel_a != "Nueva Venta":
            auto_id = int(sel_a.split("–")[0].replace("#", "").strip())
            a = next((x for x in autos_lista if x["id"] == auto_id), {})

        col1, col2 = st.columns(2)
        with col1:
            fecha_a = st.date_input("Fecha de venta", value=date.fromisoformat(a["fecha"]) if a.get("fecha") else date.today(), key="a_fecha")
            unidad = st.text_input("Unidad (ej. Toyota Corolla 2020)", value=a.get("unidad", ""), key="a_unidad")
            tipo_auto = st.radio("Tipo", ["Propio", "Consignación"], index=0 if a.get("tipo","Propio")=="Propio" else 1, horizontal=True, key="a_tipo")
        with col2:
            costo_a = st.number_input("Costo de la unidad ($)", min_value=0.0, value=float(a.get("costo", 0)), step=500.0, key="a_costo")
            utilidad_a = st.number_input("Utilidad ($)", min_value=0.0, value=float(a.get("utilidad", 0)), step=100.0, key="a_util")
            notas_a = st.text_input("Notas", value=a.get("notas") or "", key="a_notas")

        st.markdown(f"**Precio de venta estimado:** {fmt_mxn(costo_a + utilidad_a)}")

        ca1, ca2 = st.columns(2)
        with ca1:
            if st.button("💾 Guardar Venta", use_container_width=True, key="a_save"):
                payload_a = {
                    "fecha": fecha_a.isoformat(),
                    "unidad": unidad,
                    "costo": costo_a,
                    "utilidad": utilidad_a,
                    "tipo": tipo_auto,
                    "notas": notas_a or None,
                }
                save_auto(payload_a, auto_id)
                log_accion(usuario_activo, "Editó auto" if auto_id else "Registró auto", "Autos",
                           f"{unidad} {tipo_auto} — Utilidad: {fmt_mxn(utilidad_a)}")
                st.success("Guardado ✓")
                st.rerun()
        with ca2:
            if auto_id and st.button("🗑️ Eliminar", use_container_width=True, key="a_del"):
                delete_auto(auto_id)
                log_accion(usuario_activo, "Eliminó auto", "Autos", f"#{auto_id} {a.get('unidad')}")
                st.warning("Eliminado.")
                st.rerun()

    # ── Tabla ─────────────────────────────────────────────────────────────────
    autos = get_autos()
    if autos:
        total_util = sum(a["utilidad"] for a in autos)
        total_ventas = len(autos)
        propios = sum(1 for a in autos if a["tipo"] == "Propio")
        consig = sum(1 for a in autos if a["tipo"] == "Consignación")

        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi("Unidades vendidas", str(total_ventas), "Total", "blue")
        with k2: kpi("Utilidad total", fmt_mxn(total_util), "Ganancia neta", "green")
        with k3: kpi("Propios", str(propios), "Vehículos propios", "purple")
        with k4: kpi("Consignación", str(consig), "Por consignar", "orange")

        st.markdown("#### Registro de ventas")
        df_a = pd.DataFrame([{
            "Fecha": a["fecha"],
            "Unidad": a["unidad"],
            "Tipo": a["tipo"],
            "Costo": fmt_mxn(a["costo"]),
            "Utilidad": fmt_mxn(a["utilidad"]),
            "Notas": a.get("notas") or "—",
        } for a in autos])

        def color_tipo(val):
            return "color:#166534" if val == "Propio" else "color:#92400e"

        st.dataframe(
            df_a.style.map(color_tipo, subset=["Tipo"]),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No hay ventas registradas aún.")
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — FACTURACIONES
# ─────────────────────────────────────────────────────────────────────────────
with tab_fact:
    st.markdown('<div class="bg-eventos">', unsafe_allow_html=True)
    st.markdown("## 🧾 Facturaciones")

    # ── Formulario ────────────────────────────────────────────────────────────
    with st.expander("➕ Registrar / Editar Facturación", expanded=False):
        facts_lista = get_facturaciones()
        opciones_f = ["Nueva Facturación"] + [
            f"#{f['id']} – {f['cliente']} ({f['tipo']}) {f['fecha']}"
            for f in facts_lista
        ]
        sel_f = st.selectbox("Seleccionar registro", opciones_f, key="f_sel")
        fact_id = None
        fac = {}
        if sel_f != "Nueva Facturación":
            fact_id = int(sel_f.split("–")[0].replace("#", "").strip())
            fac = next((x for x in facts_lista if x["id"] == fact_id), {})

        col1, col2 = st.columns(2)
        with col1:
            fecha_f = st.date_input("Fecha", value=date.fromisoformat(fac["fecha"]) if fac.get("fecha") else date.today(), key="f_fecha")
            cliente_f = st.text_input("Cliente", value=fac.get("cliente", ""), key="f_cliente")
            unidad_f = st.text_input("Unidad / Descripción", value=fac.get("unidad") or "", key="f_unidad")
        with col2:
            tipo_f = st.selectbox("Tipo de facturación", ["Crédito", "Placas", "Impuestos"],
                index=["Crédito", "Placas", "Impuestos"].index(fac["tipo"]) if fac.get("tipo") in ["Crédito", "Placas", "Impuestos"] else 0,
                key="f_tipo")
            monto_f = st.number_input("Monto ($)", min_value=0.0, value=float(fac.get("monto", 0)), step=100.0, key="f_monto")
            notas_f = st.text_input("Notas", value=fac.get("notas") or "", key="f_notas")

        cf1, cf2 = st.columns(2)
        with cf1:
            if st.button("💾 Guardar Facturación", use_container_width=True, key="f_save"):
                payload_f = {
                    "fecha": fecha_f.isoformat(),
                    "cliente": cliente_f,
                    "unidad": unidad_f or None,
                    "tipo": tipo_f,
                    "monto": monto_f,
                    "notas": notas_f or None,
                }
                save_facturacion(payload_f, fact_id)
                log_accion(usuario_activo, "Editó facturación" if fact_id else "Registró facturación", "Facturaciones",
                           f"{cliente_f} — {tipo_f} — {fmt_mxn(monto_f)}")
                st.success("Guardado ✓")
                st.rerun()
        with cf2:
            if fact_id and st.button("🗑️ Eliminar", use_container_width=True, key="f_del"):
                delete_facturacion(fact_id)
                log_accion(usuario_activo, "Eliminó facturación", "Facturaciones", f"#{fact_id} {fac.get('cliente')}")
                st.warning("Eliminado.")
                st.rerun()

    # ── Tabla ─────────────────────────────────────────────────────────────────
    facts = get_facturaciones()
    if facts:
        total_f = sum(f["monto"] for f in facts)
        creditos = sum(f["monto"] for f in facts if f["tipo"] == "Crédito")
        placas   = sum(f["monto"] for f in facts if f["tipo"] == "Placas")
        imptos   = sum(f["monto"] for f in facts if f["tipo"] == "Impuestos")

        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi("Total facturado", fmt_mxn(total_f), f"{len(facts)} facturas", "green")
        with k2: kpi("Crédito", fmt_mxn(creditos), f"{sum(1 for f in facts if f['tipo']=='Crédito')} facturas", "blue")
        with k3: kpi("Placas", fmt_mxn(placas), f"{sum(1 for f in facts if f['tipo']=='Placas')} facturas", "purple")
        with k4: kpi("Impuestos", fmt_mxn(imptos), f"{sum(1 for f in facts if f['tipo']=='Impuestos')} facturas", "orange")

        st.markdown("#### Registro de facturaciones")
        TIPO_COLOR = {"Crédito": "color:#1e40af", "Placas": "color:#6b21a8", "Impuestos": "color:#92400e"}
        df_f = pd.DataFrame([{
            "Fecha": f["fecha"],
            "Cliente": f["cliente"],
            "Unidad": f.get("unidad") or "—",
            "Tipo": f["tipo"],
            "Monto": fmt_mxn(f["monto"]),
            "Notas": f.get("notas") or "—",
        } for f in facts])

        st.dataframe(
            df_f.style.map(lambda v: TIPO_COLOR.get(v, ""), subset=["Tipo"]),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No hay facturaciones registradas aún.")
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — HISTORIAL  (fondo amarillo claro)
# ─────────────────────────────────────────────────────────────────────────────
with tab_hist:
    st.markdown('<div class="bg-hist">', unsafe_allow_html=True)
    st.markdown("### 📋 Historial de Cambios")
    st.caption("Registro automático de cada modificación — quién, qué, cuándo.")

    historial = get_historial()
    if historial:
        df_h = pd.DataFrame(historial)[["fecha", "usuario", "modulo", "accion", "detalle"]]
        df_h.columns = ["Fecha", "Usuario", "Módulo", "Acción", "Detalle"]

        # Filtros rápidos
        fc1, fc2 = st.columns(2)
        with fc1:
            mod_fil = st.multiselect("Filtrar por módulo", ["Eventos", "Rentas", "Autos", "Facturaciones"], default=["Eventos", "Rentas", "Autos", "Facturaciones"])
        with fc2:
            usr_fil = st.text_input("Filtrar por usuario", placeholder="Escribe un nombre...")

        df_f = df_h[df_h["Módulo"].isin(mod_fil)] if mod_fil else df_h
        if usr_fil:
            df_f = df_f[df_f["Usuario"].str.contains(usr_fil, case=False, na=False)]

        st.dataframe(df_f, use_container_width=True, hide_index=True)
        st.caption(f"Mostrando {len(df_f)} de {len(df_h)} registros")
    else:
        st.info("Aún no hay cambios registrados. Cada vez que alguien guarde o elimine algo, aparecerá aquí.")
    st.markdown('</div>', unsafe_allow_html=True)
