import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "finanzas.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
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


init_db()
