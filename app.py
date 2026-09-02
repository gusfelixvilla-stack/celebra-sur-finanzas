import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
from database import (
    init_db, USE_SUPABASE,
    log_accion, get_eventos, get_rentas, get_historial,
    save_evento, delete_evento, save_renta, delete_renta,
    get_autos, save_auto, delete_auto,
    get_facturaciones, save_facturacion, delete_facturacion,
    get_cierres, save_cierre, delete_cierre,
    get_gastos, save_gasto, delete_gasto,
    get_patrimonio, save_patrimonio, delete_patrimonio,
)
from contract import generar_contrato

init_db()

# ── Caché 60s — evita re-consultar Supabase en cada interacción ──────────────
@st.cache_data(ttl=60)
def _c_eventos(): return get_eventos()

@st.cache_data(ttl=60)
def _c_rentas(): return get_rentas()

@st.cache_data(ttl=60)
def _c_autos(): return get_autos()

@st.cache_data(ttl=60)
def _c_facturaciones(): return get_facturaciones()

@st.cache_data(ttl=60)
def _c_historial(): return get_historial()

@st.cache_data(ttl=60)
def _c_cierres(): return get_cierres()

@st.cache_data(ttl=60)
def _c_gastos(): return get_gastos()

@st.cache_data(ttl=60)
def _c_patrimonio(): return get_patrimonio()

# Histórico de ventas de autos reconstruido del Excel AUTO FACIL (archivo estático,
# no vive en Supabase para no mezclarse con los KPIs del mes en curso).
@st.cache_data
def _c_historico_autos():
    ruta = Path(__file__).parent / "data" / "historico_autos.csv"
    if not ruta.exists():
        return None
    return pd.read_csv(ruta)

# Meses que realmente existen como hoja en el Excel. No se puede deducir del CSV
# porque hay meses con hoja y cero ventas (marzo 2025), y sin esto el promedio
# mensual sale inflado.
@st.cache_data
def _c_historico_meses():
    ruta = Path(__file__).parent / "data" / "historico_autos_meses.csv"
    if not ruta.exists():
        return None
    return pd.read_csv(ruta).set_index("anio")["meses_con_hoja"].to_dict()

def _clear_cache():
    for fn in [_c_eventos, _c_rentas, _c_autos, _c_facturaciones,
               _c_historial, _c_cierres, _c_gastos, _c_patrimonio]:
        fn.clear()

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

  /* ── Móvil: tarjetas KPI en 2 columnas en vez de apiladas ── */
  @media (max-width: 640px) {
    [data-testid="stHorizontalBlock"] {
      flex-wrap: wrap !important;
      gap: 8px !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
      min-width: 46% !important;
      flex: 1 1 46% !important;
      width: 46% !important;
    }
  }
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
                                placeholder="Escribe tu nombre", key="_nombre_input",
                                help="Se usa para registrar en el Historial quién hizo cada cambio.")
        if nombre != st.session_state.usuario:
            st.session_state.usuario = nombre
        if not nombre.strip():
            st.caption("⚠️ Sin nombre, tus cambios se guardan como \"Anónimo\" en el Historial.")
    with col_title:
        st.markdown("# 💰 Control Financiero")

usuario_activo = st.session_state.usuario.strip() or "Anónimo"

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def fmt_mxn(n):
    if n is None: return "$0"
    return f"${n:,.0f}"


def fmt_md(n):
    """Igual que fmt_mxn pero seguro dentro de texto markdown (evita modo LaTeX)."""
    return fmt_mxn(n).replace("$", "\\$")


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

    # Sufijo único por propiedad (no solo por mes) — evita que las 3 casas
    # compartan las mismas clases CSS y se pisen los colores entre sí.
    slug = "".join(ch for ch in propiedad.lower() if ch.isalnum()) + f"-{mes}"

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
      .rcal-{slug} {{ background:#ffffff; border-radius:14px; padding:14px 10px;
                     box-shadow:0 2px 8px rgba(0,0,0,.08); margin-bottom:8px; }}
      .rcal-title-{slug} {{ text-align:center; font-size:.95rem; font-weight:700;
                           color:{c_oscuro}; margin-bottom:8px; }}
      .rcal-grid-{slug} {{ display:grid; grid-template-columns:repeat(7,1fr); gap:3px; }}
      .rcal-head-{slug} {{ text-align:center; font-size:.7rem; font-weight:600;
                          color:#64748b; padding:3px 0; }}
      .rcal-day-{slug} {{ text-align:center; border-radius:7px; padding:5px 2px;
                         font-size:.8rem; }}
      .rcal-libre-{slug} {{ background:{c_fondo}; color:{c_oscuro}; font-weight:600; }}
      .rcal-ocup-{slug}  {{ background:{c_acento}; color:#fff; font-weight:700;
                           border-radius:7px; cursor:default; }}
      .rcal-hoy-{slug}   {{ background:#1e40af; color:#fff; font-weight:700; border-radius:50%;}}
      .rcal-pas-{slug}   {{ color:#cbd5e1; }}
      .rcal-vacio-{slug} {{ visibility:hidden; }}
      .rcal-legend-{slug} {{ display:flex; gap:10px; justify-content:center;
                            margin-top:8px; font-size:.72rem; color:#475569; }}
      .rdot {{ width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:3px; }}
    </style>
    <div class="rcal-{slug}">
      <div class="rcal-title-{slug}">📅 {MESES_ES[mes-1]} {anio}</div>
      <div class="rcal-grid-{slug}">
    """
    for d in DIAS_ES:
        html += f'<div class="rcal-head-{slug}">{d}</div>'

    for semana in cal:
        for dia in semana:
            if dia == 0:
                html += f'<div class="rcal-day-{slug} rcal-vacio-{slug}">·</div>'
                continue
            d = date(anio, mes, dia)
            if d in ocupadas:
                html += f'<div class="rcal-day-{slug} rcal-ocup-{slug}" title="{ocupadas[d]}">🔴{dia}</div>'
            elif d == hoy:
                html += f'<div class="rcal-day-{slug} rcal-hoy-{slug}">{dia}</div>'
            elif d < hoy:
                html += f'<div class="rcal-day-{slug} rcal-pas-{slug}">{dia}</div>'
            else:
                html += f'<div class="rcal-day-{slug} rcal-libre-{slug}">{dia}</div>'

    html += f"""
      </div>
      <div class="rcal-legend-{slug}">
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
    detalle_eventos, detalle_rentas, detalle_autos, detalle_facts = [], [], [], []
    total_eventos = total_rentas = total_autos = total_facts = 0

    for e in _c_eventos():
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

    for r in _c_rentas():
        if r["fecha_ingreso_real"] == dia_str:
            total_rentas += r["monto_renta"]
            detalle_rentas.append({"Propiedad": r["propiedad"], "Vencimiento": r["fecha_vencimiento"], "Monto": r["monto_renta"]})

    for a in _c_autos():
        if a["fecha"] == dia_str:
            total_autos += a["utilidad"]
            detalle_autos.append({"Unidad": a["unidad"], "Tipo": a["tipo"], "Utilidad": a["utilidad"]})

    for f in _c_facturaciones():
        if f["fecha"] == dia_str:
            total_facts += f["monto"]
            detalle_facts.append({"Cliente": f["cliente"], "Tipo": f["tipo"], "Monto": f["monto"]})

    total = total_eventos + total_rentas + total_autos + total_facts
    return total, total_eventos, total_rentas, total_autos, total_facts, detalle_eventos, detalle_rentas, detalle_autos, detalle_facts


# ══════════════════════════════════════════════════════════════════════════════
# TABS — controladas por session_state para poder saltar de una a otra
# desde botones (ej. "Modificar →" en las alertas del Dashboard)
# ══════════════════════════════════════════════════════════════════════════════
NOMBRES_TABS = ["📊 Dashboard", "🎉 Eventos", "🏠 Rentas", "🚗 Autos", "🧾 Facturaciones", "💸 Gastos", "🏦 Patrimonio", "📋 Historial"]
if "tab_activa" not in st.session_state:
    st.session_state.tab_activa = NOMBRES_TABS[0]
# "_pending_tab" se aplica ANTES de dibujar el control, porque Streamlit no
# permite modificar session_state de un widget después de instanciarlo.
if "_pending_tab" in st.session_state:
    st.session_state["tab_activa"] = st.session_state.pop("_pending_tab")

tab_sel = st.segmented_control(
    "Navegación", NOMBRES_TABS, key="tab_activa", label_visibility="collapsed"
)
if tab_sel is None:
    tab_sel = NOMBRES_TABS[0]

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DASHBOARD  (fondo azul cielo)
# ─────────────────────────────────────────────────────────────────────────────
if tab_sel == "📊 Dashboard":

    # ── Datos globales ────────────────────────────────────────────────────────
    todos_ev    = _c_eventos()
    todas_rent  = _c_rentas()
    todos_autos = _c_autos()
    todas_facts = _c_facturaciones()
    todos_gastos = _c_gastos()

    total_pactado  = sum(e["costo_total"] for e in todos_ev)
    total_cobrado  = sum(
        e["monto_apartado"] + (e["costo_total"] - e["monto_apartado"]
        if e["estatus"] == "Liquidado" else 0)
        for e in todos_ev
    )
    total_util_ev     = sum(e.get("utilidad", 0) for e in todos_ev)
    rent_cobradas     = sum(r["monto_renta"] for r in todas_rent if r["fecha_ingreso_real"])
    util_autos        = sum(a["utilidad"] for a in todos_autos)
    total_facts_monto = sum(f["monto"] for f in todas_facts)
    total_gastos_monto = sum(g["monto"] for g in todos_gastos)

    total_ingresos   = total_util_ev + util_autos + rent_cobradas + total_facts_monto
    utilidad_neta    = total_ingresos - total_gastos_monto

    # ── Totales del mes en curso (para el banner) ─────────────────────────────
    MESES_NOMBRES_BANNER = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    _hoy_banner = date.today()
    _mes_banner_str = _hoy_banner.strftime("%Y-%m")

    util_ev_mes = sum(
        e.get("utilidad", 0) for e in todos_ev
        if (e.get("fecha_apartado") or "")[:7] == _mes_banner_str
        or (e.get("fecha_liquidacion") or "")[:7] == _mes_banner_str
    )
    rent_cobradas_mes = sum(
        r["monto_renta"] for r in todas_rent
        if (r.get("fecha_ingreso_real") or "")[:7] == _mes_banner_str
    )
    util_autos_mes = sum(
        a["utilidad"] for a in todos_autos if (a.get("fecha") or "")[:7] == _mes_banner_str
    )
    total_facts_mes = sum(
        f["monto"] for f in todas_facts if (f.get("fecha") or "")[:7] == _mes_banner_str
    )
    total_gastos_mes = sum(
        g["monto"] for g in todos_gastos if (g.get("fecha") or "")[:7] == _mes_banner_str
    )
    total_ingresos_mes = util_ev_mes + util_autos_mes + rent_cobradas_mes + total_facts_mes
    utilidad_neta_mes   = total_ingresos_mes - total_gastos_mes

    # ── Alertas automáticas ──────────────────────────────────────────────────
    # Cada alerta guarda a qué registro/módulo lleva, para poder saltar
    # directo a modificarlo con un botón ("Modificar →").
    _alertas = []
    for _r in todas_rent:
        if not _r["fecha_ingreso_real"]:
            _est_r = estatus_renta(_r["fecha_vencimiento"], None)
            if _est_r == "Atrasado":
                _alertas.append({
                    "texto": f"🔴 <b>{_r['propiedad']}</b> — renta vencida el {_r['fecha_vencimiento']} ({fmt_mxn(_r['monto_renta'])})",
                    "tipo": "renta", "id": _r["id"],
                })
            elif _est_r == "Pendiente":
                _dias_r = (date.fromisoformat(_r["fecha_vencimiento"]) - date.today()).days
                if _dias_r <= 5:
                    _alertas.append({
                        "texto": f"🟡 <b>{_r['propiedad']}</b> — renta vence en {_dias_r} días ({fmt_mxn(_r['monto_renta'])})",
                        "tipo": "renta", "id": _r["id"],
                    })
    for _e in todos_ev:
        if _e["estatus"] == "Apartado" and _e.get("fecha_evento"):
            _dias_e = (date.fromisoformat(_e["fecha_evento"]) - date.today()).days
            _saldo_e = _e["costo_total"] - _e["monto_apartado"]
            if _saldo_e > 0:
                if -7 <= _dias_e < 0:
                    _alertas.append({
                        "texto": f"🔴 <b>{_e['concepto']}</b> — evento hace {-_dias_e}d, saldo pendiente {fmt_mxn(_saldo_e)}",
                        "tipo": "evento", "id": _e["id"],
                    })
                elif 0 <= _dias_e <= 3:
                    _alertas.append({
                        "texto": f"🟡 <b>{_e['concepto']}</b> — evento en {_dias_e}d, cobrar saldo {fmt_mxn(_saldo_e)}",
                        "tipo": "evento", "id": _e["id"],
                    })
    if _alertas:
        st.markdown(
            """<div style="background:#fef2f2;border:1.5px solid #fca5a5;border-radius:12px 12px 0 0;
            padding:14px 18px 4px 18px;">
            <b style="color:#991b1b;">⚠️ Alertas</b>
            </div>""", unsafe_allow_html=True)
        st.markdown(
            '<div style="background:#fef2f2;border:1.5px solid #fca5a5;border-top:none;'
            'padding:2px 18px 14px 18px;margin-bottom:16px;">',
            unsafe_allow_html=True,
        )
        for _i, _al in enumerate(_alertas):
            _ac1, _ac2 = st.columns([5, 1.3])
            with _ac1:
                st.markdown(f"<div style='padding-top:6px'>{_al['texto']}</div>", unsafe_allow_html=True)
            with _ac2:
                if st.button("Modificar →", key=f"alerta_ir_{_al['tipo']}_{_al['id']}_{_i}",
                              use_container_width=True):
                    if _al["tipo"] == "renta":
                        st.session_state["_jump_renta_id"] = _al["id"]
                        st.session_state["_pending_tab"] = "🏠 Rentas"
                    else:
                        st.session_state["_jump_evento_id"] = _al["id"]
                        st.session_state["_pending_tab"] = "🎉 Eventos"
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Banner de utilidad neta — cambia entre "Este mes" y "Acumulado" ───────
    vista_banner = st.radio(
        "Ver utilidad neta:", ["📅 Este mes", "📊 Acumulado histórico"],
        horizontal=True, key="vista_banner", label_visibility="collapsed",
    )

    if vista_banner == "📅 Este mes":
        _titulo_banner = f"💰 UTILIDAD NETA — {MESES_NOMBRES_BANNER[_hoy_banner.month-1].upper()} {_hoy_banner.year}"
        _monto_banner   = utilidad_neta_mes
        _ing_banner     = total_ingresos_mes
        _gas_banner     = total_gastos_mes
        _ev_banner      = util_ev_mes
        _rent_banner    = rent_cobradas_mes
        _auto_banner    = util_autos_mes
        _fact_banner    = total_facts_mes
    else:
        _titulo_banner = "💰 UTILIDAD NETA ACUMULADA"
        _monto_banner   = utilidad_neta
        _ing_banner     = total_ingresos
        _gas_banner     = total_gastos_monto
        _ev_banner      = total_util_ev
        _rent_banner    = rent_cobradas
        _auto_banner    = util_autos
        _fact_banner    = total_facts_monto

    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);
        border-radius:16px;padding:20px 28px;margin-bottom:18px;text-align:center;">
        <div style="color:#bfdbfe;font-size:0.85rem;font-weight:600;letter-spacing:1px;
        text-transform:uppercase;">{_titulo_banner}</div>
        <div style="color:#ffffff;font-size:2.4rem;font-weight:800;margin:6px 0;">
        {fmt_mxn(_monto_banner)}</div>
        <div style="color:#93c5fd;font-size:0.8rem;">
        Ingresos {fmt_mxn(_ing_banner)} &nbsp;−&nbsp;
        Gastos <span style="color:#fca5a5">{fmt_mxn(_gas_banner)}</span>
        </div><div style="color:#93c5fd;font-size:0.75rem;margin-top:4px;">
        Eventos {fmt_mxn(_ev_banner)} &nbsp;+&nbsp;
        Rentas {fmt_mxn(_rent_banner)} &nbsp;+&nbsp;
        Autos {fmt_mxn(_auto_banner)} &nbsp;+&nbsp;
        Facturaciones {fmt_mxn(_fact_banner)}
        </div></div>""",
        unsafe_allow_html=True
    )

    # ── Búsqueda global ──────────────────────────────────────────────────────
    _q = st.text_input("🔍 Buscar en todos los módulos",
                        placeholder="Cliente, propiedad, unidad, concepto...",
                        key="dash_search", label_visibility="visible")
    if _q:
        _ql = _q.lower()
        _res = []
        for _e in todos_ev:
            if _ql in (_e.get("concepto") or "").lower():
                _res.append({"Módulo": "🎉 Evento", "Concepto": _e["concepto"],
                             "Fecha": _e["fecha_evento"], "Monto": fmt_mxn(_e["costo_total"])})
        for _r in todas_rent:
            if _ql in (_r.get("propiedad") or "").lower() or _ql in (_r.get("notas") or "").lower():
                _res.append({"Módulo": "🏠 Renta", "Concepto": _r["propiedad"],
                             "Fecha": _r["fecha_vencimiento"], "Monto": fmt_mxn(_r["monto_renta"])})
        for _a in todos_autos:
            if _ql in (_a.get("unidad") or "").lower() or _ql in (_a.get("notas") or "").lower():
                _res.append({"Módulo": "🚗 Auto", "Concepto": _a["unidad"],
                             "Fecha": _a["fecha"], "Monto": fmt_mxn(_a["utilidad"])})
        for _f in todas_facts:
            if _ql in (_f.get("cliente") or "").lower() or _ql in (_f.get("unidad") or "").lower():
                _res.append({"Módulo": "🧾 Facturación", "Concepto": _f["cliente"],
                             "Fecha": _f["fecha"], "Monto": fmt_mxn(_f["monto"])})
        for _g in todos_gastos:
            if _ql in (_g.get("concepto") or "").lower() or _ql in (_g.get("modulo") or "").lower():
                _res.append({"Módulo": "💸 Gasto", "Concepto": _g["concepto"],
                             "Fecha": _g["fecha"], "Monto": fmt_mxn(_g["monto"])})
        if _res:
            st.dataframe(pd.DataFrame(_res), use_container_width=True, hide_index=True)
        else:
            st.caption(f"Sin resultados para «{_q}»")

    st.markdown("### 📊 Resumen General")
    g1, g2, g3, g4, g5, g6, g7 = st.columns(7)
    with g1: kpi("Eventos pactados", fmt_mxn(total_pactado), f"{len(todos_ev)} eventos", "blue")
    with g2: kpi("Cobrado eventos", fmt_mxn(total_cobrado), "Apartados + liquidados", "green")
    with g3: kpi("Rentas cobradas", fmt_mxn(rent_cobradas), f"{sum(1 for r in todas_rent if r['fecha_ingreso_real'])} pagos", "purple")
    with g4: kpi("Utilidades eventos", fmt_mxn(total_util_ev), "Ganancia neta", "orange")
    with g5: kpi("Utilidad autos", fmt_mxn(util_autos), f"{len(todos_autos)} ventas", "green")
    with g6: kpi("Facturaciones", fmt_mxn(total_facts_monto), f"{len(todas_facts)} facturas", "blue")
    with g7: kpi("Total gastos", fmt_mxn(total_gastos_monto), f"{len(todos_gastos)} registros", "orange")

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

    total, tot_ev, tot_rent, tot_autos, tot_facts, det_ev, det_rent, det_autos, det_facts = ingresos_del_dia(dia_sel)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi("Total del día", fmt_mxn(total), dia_sel.strftime("%d/%m/%Y"), "green")
    with c2: kpi("Eventos", fmt_mxn(tot_ev), f"{len(det_ev)} mov.", "blue")
    with c3: kpi("Rentas", fmt_mxn(tot_rent), f"{len(det_rent)} prop.", "purple")
    with c4: kpi("Autos", fmt_mxn(tot_autos), f"{len(det_autos)} ventas", "orange")
    with c5: kpi("Facturaciones", fmt_mxn(tot_facts), f"{len(det_facts)} fact.", "blue")

    if det_ev:
        st.markdown("##### Desglose Eventos")
        df = pd.DataFrame(det_ev); df["Monto"] = df["Monto"].apply(fmt_mxn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    if det_rent:
        st.markdown("##### Desglose Rentas")
        df = pd.DataFrame(det_rent); df["Monto"] = df["Monto"].apply(fmt_mxn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    if det_autos:
        st.markdown("##### Desglose Autos")
        df = pd.DataFrame(det_autos); df["Utilidad"] = df["Utilidad"].apply(fmt_mxn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    if det_facts:
        st.markdown("##### Desglose Facturaciones")
        df = pd.DataFrame(det_facts); df["Monto"] = df["Monto"].apply(fmt_mxn)
        st.dataframe(df, use_container_width=True, hide_index=True)
    if not det_ev and not det_rent and not det_autos and not det_facts:
        st.info("Sin ingresos en esa fecha.")

    st.markdown("---")
    st.markdown("##### Últimos 7 días")
    resumen = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        t, te, tr, ta, tf, _, _, _, _ = ingresos_del_dia(d)
        resumen.append({"Fecha": d.strftime("%d/%m"), "Eventos": te, "Rentas": tr, "Autos": ta, "Facturaciones": tf})
    st.bar_chart(pd.DataFrame(resumen).set_index("Fecha"))

    # ── Flujo de caja proyectado ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💸 Flujo de Caja — Próximos 30 días")
    _fin30 = date.today() + timedelta(days=30)
    _proyeccion = []
    for _e in todos_ev:
        if _e["estatus"] == "Apartado" and _e.get("fecha_evento"):
            _fe = date.fromisoformat(_e["fecha_evento"])
            if date.today() <= _fe <= _fin30:
                _saldo = _e["costo_total"] - _e["monto_apartado"]
                if _saldo > 0:
                    _proyeccion.append({"Fecha": _fe.isoformat(), "Tipo": "🎉 Evento",
                                        "Concepto": _e["concepto"], "Esperado": _saldo})
    for _r in todas_rent:
        if not _r["fecha_ingreso_real"]:
            _fv = date.fromisoformat(_r["fecha_vencimiento"])
            if date.today() <= _fv <= _fin30:
                _proyeccion.append({"Fecha": _fv.isoformat(), "Tipo": "🏠 Renta",
                                    "Concepto": _r["propiedad"], "Esperado": _r["monto_renta"]})
    _proyeccion.sort(key=lambda x: x["Fecha"])
    _total_proy = sum(p["Esperado"] for p in _proyeccion)
    pf1, pf2 = st.columns([1, 3])
    with pf1:
        kpi("Esperado próx. 30d", fmt_mxn(_total_proy), f"{len(_proyeccion)} cobros", "green")
    with pf2:
        if _proyeccion:
            _df_proy = pd.DataFrame(_proyeccion)
            _df_proy["Esperado"] = _df_proy["Esperado"].apply(fmt_mxn)
            st.dataframe(_df_proy, use_container_width=True, hide_index=True)
        else:
            st.info("No hay cobros pendientes en los próximos 30 días.")

    # ── Botón descargar Excel ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Descargar respaldo")
    import io
    buffer = io.BytesIO()
    tablas = {
        "Eventos": _c_eventos(),
        "Rentas": _c_rentas(),
        "Autos": _c_autos(),
        "Facturaciones": _c_facturaciones(),
        "Gastos": _c_gastos(),
        "Historial": _c_historial(),
    }
    try:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for nombre, datos in tablas.items():
                df = pd.DataFrame(datos) if datos else pd.DataFrame(["Sin datos"], columns=["Info"])
                df.to_excel(writer, sheet_name=nombre, index=False)
        buffer.seek(0)
        st.download_button(
            label="📥 Descargar todo en Excel",
            data=buffer,
            file_name=f"celebrasur_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False,
        )
    except Exception as _ex_xlsx:
        st.caption(f"⚠️ Respaldo Excel no disponible: {_ex_xlsx}")

    # ── Resumen Mensual ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📆 Resumen Mensual")

    hoy_mes = date.today()
    mes_actual_str = hoy_mes.strftime("%Y-%m")
    MESES_NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

    # Calcular totales reales para cualquier mes desde las transacciones
    def _total_mes(anio_mes: str) -> dict:
        ev = sum(
            (e["monto_apartado"] or 0) + ((e["costo_total"] - e["monto_apartado"])
            if e["estatus"] == "Liquidado" else 0)
            for e in _c_eventos()
            if (e.get("fecha_apartado") or "")[:7] == anio_mes or
               (e.get("fecha_liquidacion") or "")[:7] == anio_mes
        )
        rent = sum(r["monto_renta"] for r in _c_rentas()
                   if (r.get("fecha_ingreso_real") or "")[:7] == anio_mes)
        autos_m = sum(a["utilidad"] for a in _c_autos()
                      if (a.get("fecha") or "")[:7] == anio_mes)
        facts_m = sum(f["monto"] for f in _c_facturaciones()
                      if (f.get("fecha") or "")[:7] == anio_mes)
        return {"eventos": ev, "rentas": rent, "autos": autos_m, "facturaciones": facts_m}

    mes_act = _total_mes(mes_actual_str)
    total_mes_act = sum(mes_act.values())

    # KPIs del mes actual
    st.markdown(f"#### 📅 {MESES_NOMBRES[hoy_mes.month-1]} {hoy_mes.year} — Mes actual (en curso)")
    ma1, ma2, ma3, ma4, ma5 = st.columns(5)
    with ma1: kpi("Total del mes", fmt_mxn(total_mes_act), "Acumulado", "green")
    with ma2: kpi("Eventos", fmt_mxn(mes_act["eventos"]), "", "blue")
    with ma3: kpi("Rentas", fmt_mxn(mes_act["rentas"]), "", "purple")
    with ma4: kpi("Autos", fmt_mxn(mes_act["autos"]), "", "orange")
    with ma5: kpi("Facturaciones", fmt_mxn(mes_act["facturaciones"]), "", "blue")

    st.markdown("---")

    # ── Capturar cierre de mes anterior ──────────────────────────────────────
    st.markdown("#### 📥 Capturar mes anterior")
    cierres = _c_cierres()
    cierres_dict = {c["anio_mes"]: c for c in cierres}

    with st.expander("➕ Registrar / Editar mes anterior", expanded=False):
        # Selector de mes (últimos 24 meses excepto el actual)
        opciones_mes = []
        for i in range(1, 25):
            d_mes = date(hoy_mes.year, hoy_mes.month, 1) - timedelta(days=i*28)
            ym = d_mes.strftime("%Y-%m")
            label = f"{MESES_NOMBRES[d_mes.month-1]} {d_mes.year}"
            if ym not in opciones_mes:
                opciones_mes.append((ym, label))
        # deduplicar
        seen = set(); opciones_mes_uniq = []
        for ym, label in opciones_mes:
            if ym not in seen:
                seen.add(ym); opciones_mes_uniq.append((ym, label))

        mes_labels = [f"{label} ({ym})" for ym, label in opciones_mes_uniq]
        sel_mes_idx = st.selectbox("Mes a registrar", range(len(mes_labels)),
                                    format_func=lambda i: mes_labels[i], key="cierre_mes_sel")
        ym_sel, _ = opciones_mes_uniq[sel_mes_idx]
        existente = cierres_dict.get(ym_sel, {})

        # Auto-calc desde registros reales
        _precalc_key = f"_precalc_{ym_sel}"
        col_auto, col_auto_info = st.columns([1, 3])
        with col_auto:
            if st.button("📊 Auto-calcular desde registros", key="c_auto", use_container_width=True):
                calc = _total_mes(ym_sel)
                st.session_state[_precalc_key] = calc
                for k in ["c_ev", "c_rent", "c_autos", "c_facts"]:
                    st.session_state.pop(k, None)
                _clear_cache(); st.rerun()
        _precalc = st.session_state.get(_precalc_key, {})
        if _precalc:
            with col_auto_info:
                st.caption(f"✅ Auto-calculado: Ev {fmt_mxn(_precalc.get('eventos',0))} · Rent {fmt_mxn(_precalc.get('rentas',0))} · Autos {fmt_mxn(_precalc.get('autos',0))} · Facts {fmt_mxn(_precalc.get('facturaciones',0))}")

        ev_default   = float(_precalc.get("eventos",      existente.get("eventos",      0)))
        rent_default = float(_precalc.get("rentas",       existente.get("rentas",       0)))
        auto_default = float(_precalc.get("autos",        existente.get("autos",        0)))
        fact_default = float(_precalc.get("facturaciones", existente.get("facturaciones", 0)))

        cm1, cm2 = st.columns(2)
        with cm1:
            ev_c   = st.number_input("Eventos ($)", min_value=0.0, value=ev_default,   step=100.0, key="c_ev")
            rent_c = st.number_input("Rentas ($)",  min_value=0.0, value=rent_default, step=100.0, key="c_rent")
        with cm2:
            autos_c = st.number_input("Autos — Utilidad ($)", min_value=0.0, value=auto_default, step=100.0, key="c_autos")
            facts_c = st.number_input("Facturaciones ($)",    min_value=0.0, value=fact_default, step=100.0, key="c_facts")
        notas_c = st.text_input("Notas del mes", value=existente.get("notas") or "", key="c_notas")

        total_c = ev_c + rent_c + autos_c + facts_c
        st.markdown(f"**Total del mes: {fmt_mxn(total_c)}**")

        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("💾 Guardar cierre", use_container_width=True, key="c_save"):
                save_cierre({"anio_mes": ym_sel, "eventos": ev_c, "rentas": rent_c,
                             "autos": autos_c, "facturaciones": facts_c, "notas": notas_c or None})
                log_accion(usuario_activo, "Guardó cierre mensual", "Dashboard", f"{ym_sel} — {fmt_mxn(total_c)}")
                st.success("Guardado ✓")
                _clear_cache(); st.rerun()
        with cc2:
            if ym_sel in cierres_dict and st.button("🗑️ Eliminar", use_container_width=True, key="c_del"):
                delete_cierre(ym_sel)
                st.warning("Eliminado.")
                _clear_cache(); st.rerun()

    # ── Gráfica comparativa de meses ─────────────────────────────────────────
    st.markdown("#### 📊 Comparativa mensual (últimos 12 meses + actual)")
    datos_grafica = []
    for ym, label in reversed(opciones_mes_uniq[:11]):
        c = cierres_dict.get(ym, {})
        datos_grafica.append({
            "Mes": label,
            "Eventos": c.get("eventos", 0),
            "Rentas": c.get("rentas", 0),
            "Autos": c.get("autos", 0),
            "Facturaciones": c.get("facturaciones", 0),
        })
    # Agregar mes actual al final
    datos_grafica.append({
        "Mes": f"{MESES_NOMBRES[hoy_mes.month-1]} {hoy_mes.year} ★",
        "Eventos": mes_act["eventos"],
        "Rentas": mes_act["rentas"],
        "Autos": mes_act["autos"],
        "Facturaciones": mes_act["facturaciones"],
    })
    df_graf = pd.DataFrame(datos_grafica).set_index("Mes")
    st.bar_chart(df_graf)

    # Tabla resumen
    if cierres:
        st.markdown("#### 📋 Historial de cierres")
        df_cierres = pd.DataFrame([{
            "Mes": f"{MESES_NOMBRES[int(c['anio_mes'].split('-')[1])-1]} {c['anio_mes'].split('-')[0]}",
            "Eventos": fmt_mxn(c.get("eventos",0)),
            "Rentas": fmt_mxn(c.get("rentas",0)),
            "Autos": fmt_mxn(c.get("autos",0)),
            "Facturaciones": fmt_mxn(c.get("facturaciones",0)),
            "Total": fmt_mxn(sum([c.get("eventos",0), c.get("rentas",0), c.get("autos",0), c.get("facturaciones",0)])),
            "Notas": c.get("notas") or "—",
        } for c in cierres])
        st.dataframe(df_cierres, use_container_width=True, hide_index=True)



# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — EVENTOS  (fondo verde clarito)
# ─────────────────────────────────────────────────────────────────────────────
if tab_sel == "🎉 Eventos":
    st.markdown("### 🎉 Local de Eventos")

    # ── Calendario de disponibilidad ──────────────────────────────────────────
    eventos_todos = _c_eventos()
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

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("◀ Mes anterior", key="cal_prev", use_container_width=True):
            if st.session_state.cal_mes == 1:
                st.session_state.cal_mes = 12
                st.session_state.cal_anio -= 1
            else:
                st.session_state.cal_mes -= 1
    with col_next:
        if st.button("Mes siguiente ▶", key="cal_next", use_container_width=True):
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
    _jump_ev_id = st.session_state.pop("_jump_evento_id", None)
    with st.expander("➕ Registrar / Editar Evento", expanded=bool(_jump_ev_id)):
        eventos_lista = _c_eventos()
        opciones = ["Nuevo Evento"] + [f"#{e['id']} – {e['concepto']} ({e['fecha_evento']})" for e in eventos_lista]
        if _jump_ev_id:
            _match_ev = next((o for o in opciones if o.startswith(f"#{_jump_ev_id} –")), None)
            if _match_ev:
                st.session_state["ev_sel"] = _match_ev
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

        if utilidad_monto > costo_total > 0:
            st.warning(
                f"⚠️ La utilidad neta ({fmt_mxn(utilidad_monto)}) es mayor que el costo "
                f"total del evento ({fmt_mxn(costo_total)}). Revisa si capturaste el "
                f"monto correcto — la utilidad debería ser una parte del costo total, no más."
            )

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
                    nuevo_id = save_evento(payload, edit_id)
                    st.session_state.fecha_presel = None
                    accion = "Editó evento" if edit_id else "Creó evento"
                    log_accion(usuario_activo, accion, "Eventos", f"{concepto} — {fmt_mxn(costo_total)}",
                               referencia_id=nuevo_id, referencia_tabla="eventos")
                    st.success("Evento guardado ✓")
                    _clear_cache(); st.rerun()
        with cd:
            if edit_id and st.button("🗑️ Eliminar", use_container_width=True, key="ev_del"):
                log_accion(usuario_activo, "Eliminó evento", "Eventos",
                           f"#{edit_id} {ev.get('concepto')} — {fmt_mxn(ev.get('costo_total',0))}",
                           referencia_id=edit_id, referencia_tabla="eventos")
                delete_evento(edit_id)
                st.warning("Evento eliminado.")
                _clear_cache(); st.rerun()

    # ── Tabla resumen ─────────────────────────────────────────────────────────
    eventos = _c_eventos()
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

    eventos_para_contrato = _c_eventos()
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



# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — RENTAS  (fondo morado lavanda)
# ─────────────────────────────────────────────────────────────────────────────
if tab_sel == "🏠 Rentas":
    st.markdown("### 🏠 Control de Rentas")

    todas_rentas = _c_rentas()

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

    col_rp, col_rn = st.columns(2)
    with col_rp:
        if st.button("◀ Mes anterior", key="rcal_prev", use_container_width=True):
            if st.session_state.rcal_mes == 1:
                st.session_state.rcal_mes = 12; st.session_state.rcal_anio -= 1
            else:
                st.session_state.rcal_mes -= 1
    with col_rn:
        if st.button("Mes siguiente ▶", key="rcal_next", use_container_width=True):
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
    _jump_r_id = st.session_state.pop("_jump_renta_id", None)
    with st.expander("➕ Registrar / Editar Renta", expanded=bool(_jump_r_id)):
        rentas_lista = _c_rentas()
        opciones_r = ["Nueva Renta"] + [
            f"#{r['id']} – {r['propiedad']} ({r.get('fecha_inicio','?')} → {r['fecha_vencimiento']})"
            for r in rentas_lista
        ]
        if _jump_r_id:
            _match_r = next((o for o in opciones_r if o.startswith(f"#{_jump_r_id} –")), None)
            if _match_r:
                st.session_state["r_sel"] = _match_r
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
                nuevo_id = save_renta(payload, rent_id)
                accion = "Editó renta" if rent_id else "Creó renta"
                log_accion(usuario_activo, accion, "Rentas",
                           f"{propiedad} {fecha_ini}→{fecha_venc} — {fmt_mxn(monto_renta)}",
                           referencia_id=nuevo_id, referencia_tabla="rentas")
                st.success("Renta guardada ✓")
                _clear_cache(); st.rerun()
        with cd2:
            if rent_id and st.button("🗑️ Eliminar", use_container_width=True, key="r_del"):
                log_accion(usuario_activo, "Eliminó renta", "Rentas",
                           f"#{rent_id} {r.get('propiedad')} {r.get('fecha_vencimiento')}",
                           referencia_id=rent_id, referencia_tabla="rentas")
                delete_renta(rent_id)
                st.warning("Eliminado.")
                _clear_cache(); st.rerun()

    # ── Tabla y KPIs ──────────────────────────────────────────────────────────
    rentas = _c_rentas()
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — AUTOS
# ─────────────────────────────────────────────────────────────────────────────
if tab_sel == "🚗 Autos":
    st.markdown("## 🚗 Utilidad por Venta de Autos")

    # ── Formulario ────────────────────────────────────────────────────────────
    with st.expander("➕ Registrar / Editar Venta", expanded=False):
        autos_lista = _c_autos()
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
                nuevo_id = save_auto(payload_a, auto_id)
                log_accion(usuario_activo, "Editó auto" if auto_id else "Registró auto", "Autos",
                           f"{unidad} {tipo_auto} — Utilidad: {fmt_mxn(utilidad_a)}",
                           referencia_id=nuevo_id, referencia_tabla="autos")
                st.success("Guardado ✓")
                _clear_cache(); st.rerun()
        with ca2:
            if auto_id and st.button("🗑️ Eliminar", use_container_width=True, key="a_del"):
                log_accion(usuario_activo, "Eliminó auto", "Autos", f"#{auto_id} {a.get('unidad')}",
                           referencia_id=auto_id, referencia_tabla="autos")
                delete_auto(auto_id)
                st.warning("Eliminado.")
                _clear_cache(); st.rerun()

    # ── Tabla ─────────────────────────────────────────────────────────────────
    autos = _c_autos()
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

    # ── Crecimiento histórico (Excel AUTO FACIL 2018–2022) ────────────────────
    st.divider()
    st.markdown("### 📈 Crecimiento histórico del lote")

    hist = _c_historico_autos()
    if hist is None or hist.empty:
        st.info("No se encontró `data/historico_autos.csv`.")
    else:
        _anios = sorted(hist["anio"].unique())
        st.caption(
            f"{len(hist)} ventas de {_anios[0]} a {_anios[-1]}, reconstruidas del Excel AUTO FACIL. "
            "Un auto vendido cuenta una sola vez aunque se repita en las hojas de los meses siguientes."
        )

        res = (hist.groupby("anio")
                   .agg(Unidades=("modelo", "size"),
                        Ventas=("venta", "sum"),
                        Costo=("costo", "sum"),
                        Utilidad=("util_neta_calc", "sum"))
                   .reset_index())
        _meses = _c_historico_meses() or {}
        _con_venta = hist.groupby("anio")["mes"].nunique().to_dict()
        res["Meses"] = res["anio"].map(lambda a: _meses.get(a) or _con_venta.get(a, 1))
        res["Ticket"] = res["Ventas"] / res["Unidades"]
        res["Margen"] = res["Utilidad"] / res["Ventas"] * 100

        h1, h2, h3, h4 = st.columns(4)
        with h1: kpi("Unidades vendidas", f"{int(res['Unidades'].sum()):,}",
                     f"{_anios[0]}–{_anios[-1]}", "blue")
        with h2: kpi("Ventas acumuladas", fmt_mxn(res["Ventas"].sum()), "Precio de venta", "purple")
        with h3: kpi("Utilidad acumulada", fmt_mxn(res["Utilidad"].sum()),
                     "Neta, ya sin comisión ni gastos", "green")
        with h4: kpi("Margen promedio",
                     f"{res['Utilidad'].sum() / res['Ventas'].sum() * 100:.1f}%",
                     "Utilidad ÷ ventas", "orange")

        cm1, cm2 = st.columns([2, 1])
        with cm1:
            metrica = st.radio(
                "Métrica", ["Unidades vendidas", "Utilidad neta", "Ventas totales"],
                horizontal=True, key="hist_metrica",
            )
        with cm2:
            base = st.radio(
                "Base", ["Total del año", "Promedio por mes"],
                horizontal=True, key="hist_base",
                help="2018 no tiene enero, 2020 no tiene enero–marzo y 2022 llega hasta mayo. "
                     "El promedio por mes compara parejo.",
            )

        _col = {"Unidades vendidas": "Unidades", "Utilidad neta": "Utilidad",
                "Ventas totales": "Ventas"}[metrica]
        graf = res[["anio", _col, "Meses"]].copy()
        if base == "Promedio por mes":
            graf[_col] = graf[_col] / graf["Meses"]
        graf["Año"] = graf["anio"].astype(str)
        st.bar_chart(graf.set_index("Año")[[_col]], color="#1d4ed8", height=320)

        _incompletos = [f"{int(r.anio)} ({int(r.Meses)} meses)"
                        for r in res.itertuples() if r.Meses < 12]
        if _incompletos:
            st.caption("⚠️ Años incompletos en el Excel: " + " · ".join(_incompletos))

        st.markdown("#### Resumen por año")
        st.dataframe(
            pd.DataFrame({
                "Año":        res["anio"].astype(str),
                "Meses":      res["Meses"],
                "Unidades":   res["Unidades"],
                "Ventas":     res["Ventas"].map(fmt_mxn),
                "Costo":      res["Costo"].map(fmt_mxn),
                "Utilidad":   res["Utilidad"].map(fmt_mxn),
                "Ticket prom.": res["Ticket"].map(fmt_mxn),
                "Margen":     res["Margen"].map(lambda x: f"{x:.1f}%"),
                "Prom. autos/mes": (res["Unidades"] / res["Meses"]).map(lambda x: f"{x:.1f}"),
            }),
            use_container_width=True, hide_index=True,
        )

        with st.expander("📅 Ver detalle mes a mes"):
            anio_sel = st.selectbox("Año", _anios, index=len(_anios) - 1, key="hist_anio")
            hm = hist[hist["anio"] == anio_sel]
            mens = (hm.groupby("mes")
                      .agg(Unidades=("modelo", "size"),
                           Utilidad=("util_neta_calc", "sum"),
                           Ventas=("venta", "sum"))
                      .reindex(range(1, 13)).fillna(0))
            # el número al frente mantiene el orden cronológico en el eje del gráfico
            mens.index = [f"{i:02d} {m[:3]}" for i, m in enumerate(MESES_ES, 1)]
            st.bar_chart(mens[[_col]], color="#1d4ed8", height=280)
            st.dataframe(
                pd.DataFrame({
                    "Mes":      MESES_ES,
                    "Unidades": mens["Unidades"].astype(int),
                    "Ventas":   mens["Ventas"].map(fmt_mxn),
                    "Utilidad": mens["Utilidad"].map(fmt_mxn),
                }),
                use_container_width=True, hide_index=True,
            )

        with st.expander("🚙 Ver las unidades vendidas"):
            anio_u = st.selectbox("Año", _anios, index=len(_anios) - 1, key="hist_anio_u")
            hu = hist[hist["anio"] == anio_u].sort_values(["mes", "modelo"])
            st.dataframe(
                pd.DataFrame({
                    "Mes":      hu["mes"].map(lambda m: MESES_ES[int(m) - 1]),
                    "Unidad":   hu["modelo"].str.title(),
                    "Modelo":   hu["anio_auto"].astype(int).astype(str),
                    "Color":    hu["color"].str.title().replace("", "—"),
                    "Costo":    hu["costo"].map(fmt_mxn),
                    "Venta":    hu["venta"].map(fmt_mxn),
                    "Utilidad": hu["util_neta_calc"].map(fmt_mxn),
                }),
                use_container_width=True, hide_index=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — FACTURACIONES
# ─────────────────────────────────────────────────────────────────────────────
if tab_sel == "🧾 Facturaciones":
    st.markdown("## 🧾 Facturaciones")

    # ── Formulario ────────────────────────────────────────────────────────────
    with st.expander("➕ Registrar / Editar Facturación", expanded=False):
        facts_lista = _c_facturaciones()
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
                nuevo_id = save_facturacion(payload_f, fact_id)
                log_accion(usuario_activo, "Editó facturación" if fact_id else "Registró facturación", "Facturaciones",
                           f"{cliente_f} — {tipo_f} — {fmt_mxn(monto_f)}",
                           referencia_id=nuevo_id, referencia_tabla="facturaciones")
                st.success("Guardado ✓")
                _clear_cache(); st.rerun()
        with cf2:
            if fact_id and st.button("🗑️ Eliminar", use_container_width=True, key="f_del"):
                log_accion(usuario_activo, "Eliminó facturación", "Facturaciones", f"#{fact_id} {fac.get('cliente')}",
                           referencia_id=fact_id, referencia_tabla="facturaciones")
                delete_facturacion(fact_id)
                st.warning("Eliminado.")
                _clear_cache(); st.rerun()

    # ── Tabla ─────────────────────────────────────────────────────────────────
    facts = _c_facturaciones()
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


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — GASTOS
# ─────────────────────────────────────────────────────────────────────────────
MODULOS_GASTO = ["Eventos", "Rentas", "Autos", "Facturaciones", "General"]

if tab_sel == "💸 Gastos":
    st.markdown("## 💸 Gastos")

    with st.expander("➕ Registrar / Editar Gasto", expanded=False):
        gastos_lista = _c_gastos()
        opciones_g = ["Nuevo Gasto"] + [
            f"#{g['id']} – {g['concepto']} ({g['fecha']})" for g in gastos_lista
        ]
        sel_g = st.selectbox("Seleccionar registro", opciones_g, key="g_sel")
        gasto_id = None
        g_data = {}
        if sel_g != "Nuevo Gasto":
            gasto_id = int(sel_g.split("–")[0].replace("#", "").strip())
            g_data = next((x for x in gastos_lista if x["id"] == gasto_id), {})

        cg1, cg2 = st.columns(2)
        with cg1:
            fecha_g = st.date_input("Fecha",
                value=date.fromisoformat(g_data["fecha"]) if g_data.get("fecha") else date.today(),
                key="g_fecha")
            modulo_g = st.selectbox("Módulo", MODULOS_GASTO,
                index=MODULOS_GASTO.index(g_data["modulo"]) if g_data.get("modulo") in MODULOS_GASTO else 4,
                key="g_modulo")
        with cg2:
            concepto_g = st.text_input("Concepto / Descripción", value=g_data.get("concepto", ""), key="g_concepto")
            monto_g = st.number_input("Monto ($)", min_value=0.0,
                value=float(g_data.get("monto", 0)), step=100.0, key="g_monto")
        notas_g = st.text_input("Notas", value=g_data.get("notas") or "", key="g_notas")

        cgs, cgd = st.columns(2)
        with cgs:
            if st.button("💾 Guardar Gasto", use_container_width=True, key="g_save"):
                if not concepto_g:
                    st.error("El concepto es obligatorio.")
                else:
                    payload_g = {
                        "fecha": fecha_g.isoformat(), "modulo": modulo_g,
                        "concepto": concepto_g, "monto": monto_g,
                        "notas": notas_g or None,
                    }
                    nuevo_gid = save_gasto(payload_g, gasto_id)
                    log_accion(usuario_activo, "Editó gasto" if gasto_id else "Registró gasto",
                               "Gastos", f"{concepto_g} — {fmt_mxn(monto_g)}",
                               referencia_id=nuevo_gid, referencia_tabla="gastos")
                    st.success("Guardado ✓")
                    _clear_cache(); st.rerun()
        with cgd:
            if gasto_id and st.button("🗑️ Eliminar", use_container_width=True, key="g_del"):
                log_accion(usuario_activo, "Eliminó gasto", "Gastos",
                           f"#{gasto_id} {g_data.get('concepto')}",
                           referencia_id=gasto_id, referencia_tabla="gastos")
                delete_gasto(gasto_id)
                st.warning("Eliminado.")
                _clear_cache(); st.rerun()

    gastos = _c_gastos()
    if gastos:
        total_g = sum(g["monto"] for g in gastos)
        g_by_mod = {}
        for g in gastos:
            g_by_mod[g["modulo"]] = g_by_mod.get(g["modulo"], 0) + g["monto"]

        cols_kg = st.columns(min(len(g_by_mod) + 1, 6))
        cols_colors = ["orange", "blue", "green", "purple", "yellow", "orange"]
        with cols_kg[0]:
            kpi("Total gastos", fmt_mxn(total_g), f"{len(gastos)} registros", "orange")
        for i, (mod, monto_mod) in enumerate(sorted(g_by_mod.items(), key=lambda x: -x[1])):
            if i + 1 < len(cols_kg):
                with cols_kg[i + 1]:
                    kpi(mod, fmt_mxn(monto_mod), "", cols_colors[i % len(cols_colors)])

        st.markdown("#### Registro de gastos")
        df_g = pd.DataFrame([{
            "Fecha": g["fecha"], "Módulo": g["modulo"],
            "Concepto": g["concepto"], "Monto": fmt_mxn(g["monto"]),
            "Notas": g.get("notas") or "—",
        } for g in gastos])
        st.dataframe(df_g, use_container_width=True, hide_index=True)

        # Mini gráfica por módulo
        if g_by_mod:
            st.markdown("#### Por módulo")
            st.bar_chart(pd.DataFrame(list(g_by_mod.items()), columns=["Módulo", "Total"]).set_index("Módulo"))
    else:
        st.info("No hay gastos registrados aún. Registra mantenimientos, insumos y otros costos aquí.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — PATRIMONIO  (activos, deudas y ratio de liquidez)
# ─────────────────────────────────────────────────────────────────────────────
CAT_ACTIVOS = ["Efectivo y bancos", "Inversiones", "Inmuebles",
               "Vehículos", "Inventario / negocio", "Otros activos"]
CAT_PASIVOS = ["Hipoteca", "Crédito automotriz", "Tarjetas de crédito",
               "Préstamos", "Otros pasivos"]
CAT_LIQUIDAS = {"Efectivo y bancos", "Inversiones"}


def por_cobrar_eventos():
    """Saldo contratado y aún no cobrado de los eventos apartados."""
    return sum(
        max(0.0, (e.get("costo_total") or 0) - (e.get("monto_apartado") or 0))
        for e in _c_eventos() if e.get("estatus") != "Liquidado"
    )


if tab_sel == "🏦 Patrimonio":
    st.markdown("## 🏦 Patrimonio y Liquidez")

    registros = _c_patrimonio()
    activos = [r for r in registros if r.get("tipo") == "Activo"]
    pasivos = [r for r in registros if r.get("tipo") == "Pasivo"]

    cxc = por_cobrar_eventos()
    total_activos = sum(r.get("monto") or 0 for r in activos) + cxc
    total_pasivos = sum(r.get("monto") or 0 for r in pasivos)
    patrimonio_neto = total_activos - total_pasivos
    liquidez = sum(r.get("monto") or 0 for r in activos if r.get("liquido"))
    liquidez_ampl = liquidez + cxc

    if patrimonio_neto > 0:
        ratio = liquidez / patrimonio_neto * 100
        ratio_ampl = liquidez_ampl / patrimonio_neto * 100
        ratio_txt = f"{ratio:.1f}%"
        ratio_sub = f"Con cuentas por cobrar: {ratio_ampl:.1f}%"
        color_ratio = "green" if ratio >= 20 else ("yellow" if ratio >= 10 else "orange")
    else:
        ratio = None
        ratio_txt = "—"
        ratio_sub = "Falta capturar activos"
        color_ratio = "blue"

    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("Activos totales", fmt_mxn(total_activos),
                 f"Incluye {fmt_mxn(cxc)} por cobrar", "blue")
    with k2: kpi("Deudas totales", fmt_mxn(total_pasivos),
                 f"{len(pasivos)} registro(s)", "orange")
    with k3: kpi("Patrimonio neto", fmt_mxn(patrimonio_neto),
                 "Activos − deudas", "purple")
    with k4: kpi("Liquidez / Patrimonio", ratio_txt, ratio_sub, color_ratio)

    # ── Lectura del ratio ─────────────────────────────────────────────────────
    if ratio is None:
        st.info("Captura abajo tu efectivo, propiedades y deudas para ver el ratio.")
    else:
        if ratio >= 20:
            st.success(
                f"**Ratio sano ({ratio_txt}).** Tienes {fmt_md(liquidez)} disponibles "
                f"de un patrimonio de {fmt_md(patrimonio_neto)}. Buen colchón para "
                "aguantar un mes flojo o aprovechar una oportunidad."
            )
        elif ratio >= 10:
            st.warning(
                f"**Ratio ajustado ({ratio_txt}).** Tu patrimonio está sano pero casi todo "
                "atorado en cosas que no se venden rápido. Si se cae un pago fuerte, "
                "andarías apretado."
            )
        else:
            st.error(
                f"**Ratio bajo ({ratio_txt}).** Solo {fmt_md(liquidez)} líquidos contra "
                f"{fmt_md(patrimonio_neto)} de patrimonio. Estás rico en papel pero corto "
                "de efectivo: cualquier imprevisto te obliga a vender algo o endeudarte."
            )
        st.caption(
            "Referencia: 20% o más es holgado, 10–20% es manejable, menos de 10% es riesgoso "
            "para un negocio con inventario y gastos fijos."
        )

    # ── Desglose ──────────────────────────────────────────────────────────────
    cA, cP = st.columns(2)
    with cA:
        st.markdown("#### 💚 Activos")
        filas_a = [{
            "Concepto": "Por cobrar de eventos",
            "Categoría": "Cuentas por cobrar",
            "Monto": fmt_mxn(cxc),
            "Líquido": "Sí (al cobrarse)",
        }] if cxc else []
        filas_a += [{
            "Concepto": r.get("nombre"),
            "Categoría": r.get("categoria"),
            "Monto": fmt_mxn(r.get("monto")),
            "Líquido": "Sí" if r.get("liquido") else "No",
        } for r in activos]
        if filas_a:
            st.dataframe(pd.DataFrame(filas_a), use_container_width=True, hide_index=True)
        else:
            st.info("Sin activos capturados.")

    with cP:
        st.markdown("#### 🔴 Deudas")
        if pasivos:
            st.dataframe(pd.DataFrame([{
                "Concepto": r.get("nombre"),
                "Categoría": r.get("categoria"),
                "Saldo": fmt_mxn(r.get("monto")),
                "Notas": r.get("notas") or "—",
            } for r in pasivos]), use_container_width=True, hide_index=True)
        else:
            st.info("Sin deudas capturadas.")

    # ── Formulario ────────────────────────────────────────────────────────────
    with st.expander("➕ Registrar / Editar activo o deuda", expanded=not registros):
        opciones_p = ["Nuevo registro"] + [
            f"#{r['id']} – {r['nombre']} ({r['tipo']})" for r in registros
        ]
        sel_p = st.selectbox("Seleccionar registro", opciones_p, key="p_sel")
        pat_id = None
        r = {}
        if sel_p != "Nuevo registro":
            pat_id = int(sel_p.split("–")[0].replace("#", "").strip())
            r = next((x for x in registros if x["id"] == pat_id), {})

        # Las llaves llevan el id del registro: así, al cambiar de registro,
        # los campos se recargan con SUS valores en vez de conservar los previos.
        sfx = f"_{pat_id}" if pat_id else "_new"

        tipo_p = st.radio("Tipo", ["Activo", "Pasivo"],
                          index=0 if r.get("tipo", "Activo") == "Activo" else 1,
                          horizontal=True, key=f"p_tipo{sfx}",
                          help="Activo = algo que tienes. Pasivo = algo que debes.")
        cats = CAT_ACTIVOS if tipo_p == "Activo" else CAT_PASIVOS

        col1, col2 = st.columns(2)
        with col1:
            categoria_p = st.selectbox(
                "Categoría", cats,
                index=cats.index(r["categoria"]) if r.get("categoria") in cats else 0,
                key=f"p_cat{sfx}")
            nombre_p = st.text_input(
                "Concepto (ej. Cuenta BBVA, Casa San Carlos)",
                value=r.get("nombre", ""), key=f"p_nombre{sfx}")
        with col2:
            monto_p = st.number_input(
                "Valor actual ($)" if tipo_p == "Activo" else "Saldo que debes ($)",
                min_value=0.0, value=float(r.get("monto", 0)), step=1000.0, key=f"p_monto{sfx}")
            notas_p = st.text_input("Notas", value=r.get("notas") or "", key=f"p_notas{sfx}")

        if tipo_p == "Activo":
            liquido_p = st.checkbox(
                "Lo puedo convertir en efectivo en menos de 30 días",
                value=bool(r.get("liquido")) if r else categoria_p in CAT_LIQUIDAS,
                key=f"p_liquido{sfx}",
                help="Marca esto solo para dinero en bancos, inversiones a la vista "
                     "y cosas que realmente venderías en un mes.")
        else:
            liquido_p = False

        cp1, cp2 = st.columns(2)
        with cp1:
            if st.button("💾 Guardar", use_container_width=True, key="p_save"):
                if not nombre_p.strip():
                    st.error("Ponle un concepto al registro.")
                else:
                    payload_p = {
                        "tipo": tipo_p,
                        "categoria": categoria_p,
                        "nombre": nombre_p.strip(),
                        "monto": monto_p,
                        "liquido": liquido_p,
                        "notas": notas_p or None,
                    }
                    nuevo_pid = save_patrimonio(payload_p, pat_id)
                    log_accion(usuario_activo,
                               "Editó patrimonio" if pat_id else "Registró patrimonio",
                               "Patrimonio", f"{tipo_p}: {nombre_p} — {fmt_mxn(monto_p)}",
                               referencia_id=nuevo_pid, referencia_tabla="patrimonio")
                    st.success("Guardado ✓")
                    _clear_cache(); st.rerun()
        with cp2:
            if pat_id and st.button("🗑️ Eliminar", use_container_width=True, key="p_del"):
                log_accion(usuario_activo, "Eliminó patrimonio", "Patrimonio",
                           f"#{pat_id} {r.get('nombre')}",
                           referencia_id=pat_id, referencia_tabla="patrimonio")
                delete_patrimonio(pat_id)
                st.warning("Eliminado.")
                _clear_cache(); st.rerun()

    st.caption(
        "ℹ️ El saldo por cobrar de eventos se toma solo de la pestaña Eventos y se actualiza "
        "automáticamente. Todo lo demás (efectivo, casas, jardín, autos personales y deudas) "
        "se captura aquí a mano — actualízalo cada vez que cambie algo grande."
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 — HISTORIAL  (fondo amarillo claro)
# ─────────────────────────────────────────────────────────────────────────────
if tab_sel == "📋 Historial":
    st.markdown("### 📋 Historial de Cambios")
    st.caption("Registro automático de cada modificación — quién, qué, cuándo.")

    from zoneinfo import ZoneInfo
    HERMOSILLO_TZ = ZoneInfo("America/Hermosillo")

    def _fmt_fecha_hist(fecha_str):
        if not fecha_str:
            return "—"
        try:
            f = fecha_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(f)
            if dt.tzinfo is not None:
                dt = dt.astimezone(HERMOSILLO_TZ)
            return dt.strftime("%d/%m/%Y %I:%M %p")
        except Exception:
            return fecha_str

    historial = _c_historial()
    if historial:
        df_h = pd.DataFrame(historial)[["fecha", "usuario", "modulo", "accion", "detalle"]]
        df_h.columns = ["Fecha", "Usuario", "Módulo", "Acción", "Detalle"]
        df_h["Fecha"] = df_h["Fecha"].apply(_fmt_fecha_hist)

        # Filtros rápidos
        fc1, fc2 = st.columns(2)
        with fc1:
            mod_fil = st.multiselect("Filtrar por módulo",
                ["Eventos", "Rentas", "Autos", "Facturaciones", "Gastos", "Dashboard"],
                default=["Eventos", "Rentas", "Autos", "Facturaciones", "Gastos", "Dashboard"])
        with fc2:
            usr_fil = st.text_input("Filtrar por usuario", placeholder="Escribe un nombre...")

        df_f = df_h[df_h["Módulo"].isin(mod_fil)] if mod_fil else df_h
        if usr_fil:
            df_f = df_f[df_f["Usuario"].str.contains(usr_fil, case=False, na=False)]

        st.dataframe(df_f, use_container_width=True, hide_index=True)
        st.caption(f"Mostrando {len(df_f)} de {len(df_h)} registros")
    else:
        st.info("Aún no hay cambios registrados. Cada vez que alguien guarde o elimine algo, aparecerá aquí.")
