"""
Capa de datos: usa Supabase (nube, persistente) si hay credenciales,
o SQLite local como respaldo para desarrollo.
"""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "finanzas.db"

# Compatibilidad
USE_POSTGRES = False
USE_SUPABASE = False


def _get_supabase_creds():
    """Lee credenciales de Supabase en tiempo de ejecución."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        try:
            import streamlit as st
            url = str(st.secrets["SUPABASE_URL"]) if "SUPABASE_URL" in st.secrets else url
            key = str(st.secrets["SUPABASE_KEY"]) if "SUPABASE_KEY" in st.secrets else key
        except Exception:
            pass
    return url, key


_sb_client = None


def _supabase():
    """Cliente Supabase (singleton)."""
    global _sb_client
    if _sb_client is None:
        from supabase import create_client
        url, key = _get_supabase_creds()
        _sb_client = create_client(url, key)
    return _sb_client


def _use_supabase():
    """¿Tenemos credenciales de Supabase?"""
    url, key = _get_supabase_creds()
    return bool(url and key)


# ── SQLite (respaldo local) ───────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


# ── Inicializar tablas SQLite ─────────────────────────────────────────────────

def init_db():
    # En Supabase las tablas se crean desde el SQL Editor
    # Solo inicializamos SQLite para desarrollo local
    if _use_supabase():
        return
    conn = get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT DEFAULT (datetime('now','localtime')),
                usuario TEXT NOT NULL DEFAULT 'Anónimo',
                accion TEXT NOT NULL,
                modulo TEXT NOT NULL,
                detalle TEXT
            );
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_evento TEXT NOT NULL,
                concepto TEXT NOT NULL,
                costo_total REAL NOT NULL,
                monto_apartado REAL NOT NULL DEFAULT 0,
                fecha_apartado TEXT,
                estatus TEXT NOT NULL DEFAULT 'Apartado',
                fecha_liquidacion TEXT,
                porcentaje_utilidad REAL NOT NULL DEFAULT 0,
                utilidad REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS rentas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                propiedad TEXT NOT NULL,
                fecha_inicio TEXT,
                fecha_vencimiento TEXT NOT NULL,
                monto_renta REAL NOT NULL,
                fecha_ingreso_real TEXT,
                notas TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
    finally:
        conn.close()


# ── API de datos ──────────────────────────────────────────────────────────────

def log_accion(usuario, accion, modulo, detalle=""):
    if _use_supabase():
        _supabase().table("historial").insert({
            "usuario": usuario, "accion": accion,
            "modulo": modulo, "detalle": detalle,
        }).execute()
    else:
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO historial (usuario,accion,modulo,detalle) VALUES (?,?,?,?)",
                (usuario, accion, modulo, detalle))
            conn.commit()
        finally:
            conn.close()


def get_eventos():
    if _use_supabase():
        r = _supabase().table("eventos").select("*").order("fecha_evento", desc=True).execute()
        return r.data or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute(
            "SELECT * FROM eventos ORDER BY fecha_evento DESC").fetchall()]
    finally:
        conn.close()


def get_rentas():
    if _use_supabase():
        r = _supabase().table("rentas").select("*").order("fecha_vencimiento", desc=True).execute()
        return r.data or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute(
            "SELECT * FROM rentas ORDER BY fecha_vencimiento DESC, propiedad").fetchall()]
    finally:
        conn.close()


def get_historial():
    if _use_supabase():
        r = _supabase().table("historial").select("*").order("id", desc=True).limit(200).execute()
        return r.data or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute(
            "SELECT * FROM historial ORDER BY id DESC LIMIT 200").fetchall()]
    finally:
        conn.close()


def save_evento(data: dict, evento_id=None):
    payload = {
        "fecha_evento": data["fecha_evento"],
        "concepto": data["concepto"],
        "costo_total": data["costo_total"],
        "monto_apartado": data["monto_apartado"],
        "fecha_apartado": data["fecha_apartado"],
        "estatus": data["estatus"],
        "fecha_liquidacion": data["fecha_liquidacion"],
        "utilidad": data["utilidad"],
    }
    if _use_supabase():
        if evento_id:
            _supabase().table("eventos").update(payload).eq("id", evento_id).execute()
        else:
            _supabase().table("eventos").insert(payload).execute()
    else:
        conn = get_conn()
        try:
            if evento_id:
                conn.execute("""UPDATE eventos SET fecha_evento=?, concepto=?,
                    costo_total=?, monto_apartado=?, fecha_apartado=?, estatus=?,
                    fecha_liquidacion=?, utilidad=? WHERE id=?""",
                    (payload["fecha_evento"], payload["concepto"], payload["costo_total"],
                     payload["monto_apartado"], payload["fecha_apartado"], payload["estatus"],
                     payload["fecha_liquidacion"], payload["utilidad"], evento_id))
            else:
                conn.execute("""INSERT INTO eventos (fecha_evento,concepto,costo_total,
                    monto_apartado,fecha_apartado,estatus,fecha_liquidacion,utilidad)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (payload["fecha_evento"], payload["concepto"], payload["costo_total"],
                     payload["monto_apartado"], payload["fecha_apartado"], payload["estatus"],
                     payload["fecha_liquidacion"], payload["utilidad"]))
            conn.commit()
        finally:
            conn.close()


def delete_evento(evento_id):
    if _use_supabase():
        _supabase().table("eventos").delete().eq("id", evento_id).execute()
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM eventos WHERE id=?", (evento_id,))
            conn.commit()
        finally:
            conn.close()


def save_renta(data: dict, renta_id=None):
    payload = {
        "propiedad": data["propiedad"],
        "fecha_inicio": data["fecha_inicio"],
        "fecha_vencimiento": data["fecha_vencimiento"],
        "monto_renta": data["monto_renta"],
        "fecha_ingreso_real": data["fecha_ingreso_real"],
        "notas": data["notas"],
    }
    if _use_supabase():
        if renta_id:
            _supabase().table("rentas").update(payload).eq("id", renta_id).execute()
        else:
            _supabase().table("rentas").insert(payload).execute()
    else:
        conn = get_conn()
        try:
            if renta_id:
                conn.execute("""UPDATE rentas SET propiedad=?, fecha_inicio=?,
                    fecha_vencimiento=?, monto_renta=?, fecha_ingreso_real=?, notas=?
                    WHERE id=?""",
                    (payload["propiedad"], payload["fecha_inicio"], payload["fecha_vencimiento"],
                     payload["monto_renta"], payload["fecha_ingreso_real"], payload["notas"], renta_id))
            else:
                conn.execute("""INSERT INTO rentas (propiedad,fecha_inicio,fecha_vencimiento,
                    monto_renta,fecha_ingreso_real,notas) VALUES (?,?,?,?,?,?)""",
                    (payload["propiedad"], payload["fecha_inicio"], payload["fecha_vencimiento"],
                     payload["monto_renta"], payload["fecha_ingreso_real"], payload["notas"]))
            conn.commit()
        finally:
            conn.close()


def delete_renta(renta_id):
    if _use_supabase():
        _supabase().table("rentas").delete().eq("id", renta_id).execute()
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM rentas WHERE id=?", (renta_id,))
            conn.commit()
        finally:
            conn.close()


# ── Autos ─────────────────────────────────────────────────────────────────────

def get_autos():
    if _use_supabase():
        r = _supabase().table("autos").select("*").order("fecha", desc=True).execute()
        return r.data or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute(
            "SELECT * FROM autos ORDER BY fecha DESC").fetchall()]
    finally:
        conn.close()


def save_auto(data: dict, auto_id=None):
    payload = {
        "fecha": data["fecha"],
        "unidad": data["unidad"],
        "costo": data["costo"],
        "utilidad": data["utilidad"],
        "tipo": data["tipo"],
        "notas": data.get("notas"),
    }
    if _use_supabase():
        if auto_id:
            _supabase().table("autos").update(payload).eq("id", auto_id).execute()
        else:
            _supabase().table("autos").insert(payload).execute()
    else:
        conn = get_conn()
        try:
            if auto_id:
                conn.execute("""UPDATE autos SET fecha=?, unidad=?, costo=?,
                    utilidad=?, tipo=?, notas=? WHERE id=?""",
                    (payload["fecha"], payload["unidad"], payload["costo"],
                     payload["utilidad"], payload["tipo"], payload["notas"], auto_id))
            else:
                conn.execute("""INSERT INTO autos (fecha,unidad,costo,utilidad,tipo,notas)
                    VALUES (?,?,?,?,?,?)""",
                    (payload["fecha"], payload["unidad"], payload["costo"],
                     payload["utilidad"], payload["tipo"], payload["notas"]))
            conn.commit()
        finally:
            conn.close()


def delete_auto(auto_id):
    if _use_supabase():
        _supabase().table("autos").delete().eq("id", auto_id).execute()
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM autos WHERE id=?", (auto_id,))
            conn.commit()
        finally:
            conn.close()


# ── Facturaciones ─────────────────────────────────────────────────────────────

def get_facturaciones():
    if _use_supabase():
        r = _supabase().table("facturaciones").select("*").order("fecha", desc=True).execute()
        return r.data or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute(
            "SELECT * FROM facturaciones ORDER BY fecha DESC").fetchall()]
    finally:
        conn.close()


def save_facturacion(data: dict, fact_id=None):
    payload = {
        "fecha": data["fecha"],
        "cliente": data["cliente"],
        "unidad": data.get("unidad"),
        "tipo": data["tipo"],
        "monto": data["monto"],
        "notas": data.get("notas"),
    }
    if _use_supabase():
        if fact_id:
            _supabase().table("facturaciones").update(payload).eq("id", fact_id).execute()
        else:
            _supabase().table("facturaciones").insert(payload).execute()
    else:
        conn = get_conn()
        try:
            if fact_id:
                conn.execute("""UPDATE facturaciones SET fecha=?, cliente=?, unidad=?,
                    tipo=?, monto=?, notas=? WHERE id=?""",
                    (payload["fecha"], payload["cliente"], payload["unidad"],
                     payload["tipo"], payload["monto"], payload["notas"], fact_id))
            else:
                conn.execute("""INSERT INTO facturaciones (fecha,cliente,unidad,tipo,monto,notas)
                    VALUES (?,?,?,?,?,?)""",
                    (payload["fecha"], payload["cliente"], payload["unidad"],
                     payload["tipo"], payload["monto"], payload["notas"]))
            conn.commit()
        finally:
            conn.close()


def delete_facturacion(fact_id):
    if _use_supabase():
        _supabase().table("facturaciones").delete().eq("id", fact_id).execute()
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM facturaciones WHERE id=?", (fact_id,))
            conn.commit()
        finally:
            conn.close()


# ── Cierres Mensuales ─────────────────────────────────────────────────────────

def get_cierres():
    if _use_supabase():
        r = _supabase().table("cierres_mensuales").select("*").order("anio_mes", desc=True).execute()
        return r.data or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute(
            "SELECT * FROM cierres_mensuales ORDER BY anio_mes DESC").fetchall()]
    finally:
        conn.close()


def save_cierre(data: dict):
    """Guarda o reemplaza el cierre de un mes (upsert por anio_mes)."""
    payload = {
        "anio_mes":      data["anio_mes"],        # "2026-05"
        "eventos":       data.get("eventos", 0),
        "rentas":        data.get("rentas", 0),
        "autos":         data.get("autos", 0),
        "facturaciones": data.get("facturaciones", 0),
        "notas":         data.get("notas"),
    }
    if _use_supabase():
        # upsert: si ya existe ese mes lo actualiza
        _supabase().table("cierres_mensuales").upsert(payload, on_conflict="anio_mes").execute()
    else:
        conn = get_conn()
        try:
            conn.execute("""INSERT INTO cierres_mensuales
                (anio_mes,eventos,rentas,autos,facturaciones,notas)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(anio_mes) DO UPDATE SET
                eventos=excluded.eventos, rentas=excluded.rentas,
                autos=excluded.autos, facturaciones=excluded.facturaciones,
                notas=excluded.notas""",
                (payload["anio_mes"], payload["eventos"], payload["rentas"],
                 payload["autos"], payload["facturaciones"], payload["notas"]))
            conn.commit()
        finally:
            conn.close()


def delete_cierre(anio_mes: str):
    if _use_supabase():
        _supabase().table("cierres_mensuales").delete().eq("anio_mes", anio_mes).execute()
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM cierres_mensuales WHERE anio_mes=?", (anio_mes,))
            conn.commit()
        finally:
            conn.close()


init_db()
