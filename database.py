import os
import sqlite3
from pathlib import Path

# ── Detectar DATABASE_URL ─────────────────────────────────────────────────────
DATABASE_URL = None

try:
    import streamlit as st
    DATABASE_URL = str(st.secrets["DATABASE_URL"]) if "DATABASE_URL" in st.secrets else None
except Exception:
    pass

if not DATABASE_URL:
    DATABASE_URL = os.environ.get("DATABASE_URL")

USE_POSTGRES = bool(DATABASE_URL)
DB_PATH = Path(__file__).parent / "finanzas.db"


# ── Conexión ──────────────────────────────────────────────────────────────────

def get_conn():
    if USE_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(
            DATABASE_URL,
            sslmode="require",
            connect_timeout=15,
        )
        conn.autocommit = False
        return conn
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


# ── Helpers SQL (SQLite usa ?, Postgres usa %s) ───────────────────────────────

def _run(sql, params=None, fetch=False):
    conn = get_conn()
    try:
        if USE_POSTGRES:
            sql = sql.replace("?", "%s")
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        if fetch:
            rows = cur.fetchall()
            if USE_POSTGRES:
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
            return [dict(r) for r in rows]
    finally:
        conn.close()


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
                )""")
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
                )""")
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
                )""")
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
