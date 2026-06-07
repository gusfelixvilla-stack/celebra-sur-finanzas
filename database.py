import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# ── Detectar si estamos en la nube (Supabase) o local (SQLite) ───────────────
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    None if not Path("/etc/streamlit/secrets.toml").exists()
    else None
)

# Intentar leer desde st.secrets si estamos en Streamlit Cloud
try:
    import streamlit as st
    DATABASE_URL = st.secrets.get("DATABASE_URL", None)
except Exception:
    pass

USE_POSTGRES = bool(DATABASE_URL)

DB_PATH = Path(__file__).parent / "finanzas.db"

# ── Conexión ─────────────────────────────────────────────────────────────────

def get_conn():
    if USE_POSTGRES:
        import psycopg2
        from urllib.parse import urlparse
        url = str(DATABASE_URL)
        r = urlparse(url)
        conn = psycopg2.connect(
            host=r.hostname,
            port=r.port or 5432,
            dbname=r.path.lstrip("/"),
            user=r.username,
            password=r.password,
            sslmode="require",
            connect_timeout=10,
        )
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn


def _exec(conn, sql, params=None):
    """Ejecuta SQL compatible con SQLite y PostgreSQL."""
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT",
                          "SERIAL PRIMARY KEY")
        sql = sql.replace("datetime('now','localtime')", "NOW()")
        sql = sql.replace("TEXT DEFAULT (NOW())", "TIMESTAMPTZ DEFAULT NOW()")
    cur = conn.cursor()
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)
    return cur


def _fetchall(cur):
    rows = cur.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in rows]
    return [dict(r) for r in rows]


# ── Inicializar tablas ────────────────────────────────────────────────────────

def init_db():
    conn = get_conn()
    try:
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS historial (
                    id SERIAL PRIMARY KEY,
                    fecha TIMESTAMPTZ DEFAULT NOW(),
                    usuario TEXT NOT NULL DEFAULT 'Anónimo',
                    accion TEXT NOT NULL,
                    modulo TEXT NOT NULL,
                    detalle TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eventos (
                    id SERIAL PRIMARY KEY,
                    fecha_evento TEXT NOT NULL,
                    concepto TEXT NOT NULL,
                    costo_total REAL NOT NULL,
                    monto_apartado REAL NOT NULL DEFAULT 0,
                    fecha_apartado TEXT,
                    estatus TEXT NOT NULL DEFAULT 'Apartado',
                    fecha_liquidacion TEXT,
                    porcentaje_utilidad REAL NOT NULL DEFAULT 0,
                    utilidad REAL NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rentas (
                    id SERIAL PRIMARY KEY,
                    propiedad TEXT NOT NULL,
                    fecha_inicio TEXT,
                    fecha_vencimiento TEXT NOT NULL,
                    monto_renta REAL NOT NULL,
                    fecha_ingreso_real TEXT,
                    notas TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            conn.commit()
        else:
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


init_db()
