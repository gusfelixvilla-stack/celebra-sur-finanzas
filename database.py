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


init_db()
