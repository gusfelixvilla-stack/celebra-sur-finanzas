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


def _use_supabase():
    """¿Tenemos credenciales de Supabase?"""
    url, key = _get_supabase_creds()
    return bool(url and key)


def _sb_get(table, order=None, limit=None):
    """SELECT * via REST API de Supabase."""
    import requests
    url, key = _get_supabase_creds()
    if not url or not key:
        return []
    endpoint = f"{url}/rest/v1/{table}?select=*"
    if order:
        endpoint += f"&order={order}"
    if limit:
        endpoint += f"&limit={limit}"
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    r = requests.get(endpoint, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def _sb_insert(table, payload):
    """INSERT via REST API de Supabase — devuelve el ID del registro creado."""
    import requests
    url, key = _get_supabase_creds()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    r = requests.post(f"{url}/rest/v1/{table}", json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    result = r.json()
    if result and isinstance(result, list):
        return result[0].get("id")
    return None


def _sb_update(table, payload, match_col, match_val):
    """UPDATE via REST API de Supabase."""
    import requests
    url, key = _get_supabase_creds()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    r = requests.patch(
        f"{url}/rest/v1/{table}?{match_col}=eq.{match_val}",
        json=payload, headers=headers, timeout=10
    )
    r.raise_for_status()


def _sb_delete(table, match_col, match_val):
    """DELETE via REST API de Supabase."""
    import requests
    url, key = _get_supabase_creds()
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    r = requests.delete(
        f"{url}/rest/v1/{table}?{match_col}=eq.{match_val}",
        headers=headers, timeout=10
    )
    r.raise_for_status()


def _sb_upsert(table, payload, on_conflict):
    """UPSERT via REST API de Supabase."""
    import requests
    url, key = _get_supabase_creds()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": f"resolution=merge-duplicates,return=minimal",
    }
    r = requests.post(
        f"{url}/rest/v1/{table}?on_conflict={on_conflict}",
        json=payload, headers=headers, timeout=10
    )
    r.raise_for_status()


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
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                modulo TEXT NOT NULL,
                concepto TEXT NOT NULL,
                monto REAL NOT NULL DEFAULT 0,
                notas TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
    finally:
        conn.close()


# ── API de datos ──────────────────────────────────────────────────────────────

def log_accion(usuario, accion, modulo, detalle="", referencia_id=None, referencia_tabla=None):
    if _use_supabase():
        payload = {"usuario": usuario, "accion": accion, "modulo": modulo, "detalle": detalle}
        if referencia_id is not None:
            payload["referencia_id"] = referencia_id
        if referencia_tabla:
            payload["referencia_tabla"] = referencia_tabla
        try:
            _sb_insert("historial", payload)
        except Exception:
            # Si faltan columnas en historial, reintenta sin campos opcionales
            try:
                _sb_insert("historial", {"usuario": usuario, "accion": accion, "modulo": modulo, "detalle": detalle})
            except Exception:
                pass
    else:
        conn = get_conn()
        try:
            conn.execute("INSERT INTO historial (usuario,accion,modulo,detalle) VALUES (?,?,?,?)",
                (usuario, accion, modulo, detalle))
            conn.commit()
        finally:
            conn.close()


def get_eventos():
    if _use_supabase():
        return _sb_get("eventos", order="fecha_evento.desc") or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute("SELECT * FROM eventos ORDER BY fecha_evento DESC").fetchall()]
    finally:
        conn.close()


def get_rentas():
    if _use_supabase():
        return _sb_get("rentas", order="fecha_vencimiento.desc") or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute("SELECT * FROM rentas ORDER BY fecha_vencimiento DESC, propiedad").fetchall()]
    finally:
        conn.close()


def get_historial():
    if _use_supabase():
        return _sb_get("historial", order="id.desc", limit=200) or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute("SELECT * FROM historial ORDER BY id DESC LIMIT 200").fetchall()]
    finally:
        conn.close()


def save_evento(data: dict, evento_id=None):
    payload = {k: data[k] for k in ["fecha_evento","concepto","costo_total","monto_apartado","fecha_apartado","estatus","fecha_liquidacion","utilidad"]}
    if _use_supabase():
        if evento_id:
            _sb_update("eventos", payload, "id", evento_id)
            return evento_id
        else:
            return _sb_insert("eventos", payload)
    else:
        conn = get_conn()
        try:
            if evento_id:
                conn.execute("""UPDATE eventos SET fecha_evento=?,concepto=?,costo_total=?,monto_apartado=?,fecha_apartado=?,estatus=?,fecha_liquidacion=?,utilidad=? WHERE id=?""",
                    (*payload.values(), evento_id))
                conn.commit()
                return evento_id
            else:
                cur = conn.execute("""INSERT INTO eventos (fecha_evento,concepto,costo_total,monto_apartado,fecha_apartado,estatus,fecha_liquidacion,utilidad) VALUES (?,?,?,?,?,?,?,?)""",
                    tuple(payload.values()))
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()


def delete_evento(evento_id):
    if _use_supabase():
        _sb_delete("eventos", "id", evento_id)
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM eventos WHERE id=?", (evento_id,)); conn.commit()
        finally:
            conn.close()


def save_renta(data: dict, renta_id=None):
    payload = {k: data[k] for k in ["propiedad","fecha_inicio","fecha_vencimiento","monto_renta","fecha_ingreso_real","notas"]}
    if _use_supabase():
        if renta_id:
            _sb_update("rentas", payload, "id", renta_id)
            return renta_id
        else:
            return _sb_insert("rentas", payload)
    else:
        conn = get_conn()
        try:
            if renta_id:
                conn.execute("""UPDATE rentas SET propiedad=?,fecha_inicio=?,fecha_vencimiento=?,monto_renta=?,fecha_ingreso_real=?,notas=? WHERE id=?""",
                    (*payload.values(), renta_id))
                conn.commit()
                return renta_id
            else:
                cur = conn.execute("""INSERT INTO rentas (propiedad,fecha_inicio,fecha_vencimiento,monto_renta,fecha_ingreso_real,notas) VALUES (?,?,?,?,?,?)""",
                    tuple(payload.values()))
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()


def delete_renta(renta_id):
    if _use_supabase():
        _sb_delete("rentas", "id", renta_id)
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM rentas WHERE id=?", (renta_id,)); conn.commit()
        finally:
            conn.close()


# ── Autos ─────────────────────────────────────────────────────────────────────

def get_autos():
    if _use_supabase():
        return _sb_get("autos", order="fecha.desc") or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute("SELECT * FROM autos ORDER BY fecha DESC").fetchall()]
    finally:
        conn.close()


def save_auto(data: dict, auto_id=None):
    payload = {k: data.get(k) for k in ["fecha","unidad","costo","utilidad","tipo","notas"]}
    if _use_supabase():
        if auto_id:
            _sb_update("autos", payload, "id", auto_id)
            return auto_id
        else:
            return _sb_insert("autos", payload)
    else:
        conn = get_conn()
        try:
            if auto_id:
                conn.execute("UPDATE autos SET fecha=?,unidad=?,costo=?,utilidad=?,tipo=?,notas=? WHERE id=?",
                    (*payload.values(), auto_id))
                conn.commit()
                return auto_id
            else:
                cur = conn.execute("INSERT INTO autos (fecha,unidad,costo,utilidad,tipo,notas) VALUES (?,?,?,?,?,?)",
                    tuple(payload.values()))
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()


def delete_auto(auto_id):
    if _use_supabase():
        _sb_delete("autos", "id", auto_id)
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM autos WHERE id=?", (auto_id,)); conn.commit()
        finally:
            conn.close()


# ── Facturaciones ─────────────────────────────────────────────────────────────

def get_facturaciones():
    if _use_supabase():
        return _sb_get("facturaciones", order="fecha.desc") or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute("SELECT * FROM facturaciones ORDER BY fecha DESC").fetchall()]
    finally:
        conn.close()


def save_facturacion(data: dict, fact_id=None):
    payload = {k: data.get(k) for k in ["fecha","cliente","unidad","tipo","monto","notas"]}
    if _use_supabase():
        if fact_id:
            _sb_update("facturaciones", payload, "id", fact_id)
            return fact_id
        else:
            return _sb_insert("facturaciones", payload)
    else:
        conn = get_conn()
        try:
            if fact_id:
                conn.execute("UPDATE facturaciones SET fecha=?,cliente=?,unidad=?,tipo=?,monto=?,notas=? WHERE id=?",
                    (*payload.values(), fact_id))
                conn.commit()
                return fact_id
            else:
                cur = conn.execute("INSERT INTO facturaciones (fecha,cliente,unidad,tipo,monto,notas) VALUES (?,?,?,?,?,?)",
                    tuple(payload.values()))
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()


def delete_facturacion(fact_id):
    if _use_supabase():
        _sb_delete("facturaciones", "id", fact_id)
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM facturaciones WHERE id=?", (fact_id,)); conn.commit()
        finally:
            conn.close()


# ── Cierres Mensuales ─────────────────────────────────────────────────────────

def get_cierres():
    if _use_supabase():
        return _sb_get("cierres_mensuales", order="anio_mes.desc") or []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute("SELECT * FROM cierres_mensuales ORDER BY anio_mes DESC").fetchall()]
    finally:
        conn.close()


def save_cierre(data: dict):
    payload = {k: data.get(k, 0) if k != "notas" and k != "anio_mes" else data.get(k)
               for k in ["anio_mes","eventos","rentas","autos","facturaciones","notas"]}
    if _use_supabase():
        _sb_upsert("cierres_mensuales", payload, "anio_mes")
    else:
        conn = get_conn()
        try:
            conn.execute("""INSERT INTO cierres_mensuales (anio_mes,eventos,rentas,autos,facturaciones,notas)
                VALUES (?,?,?,?,?,?) ON CONFLICT(anio_mes) DO UPDATE SET
                eventos=excluded.eventos,rentas=excluded.rentas,
                autos=excluded.autos,facturaciones=excluded.facturaciones,notas=excluded.notas""",
                tuple(payload.values()))
            conn.commit()
        finally:
            conn.close()


def delete_cierre(anio_mes: str):
    if _use_supabase():
        _sb_delete("cierres_mensuales", "anio_mes", anio_mes)
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM cierres_mensuales WHERE anio_mes=?", (anio_mes,)); conn.commit()
        finally:
            conn.close()


# ── Gastos ────────────────────────────────────────────────────────────────────

def get_gastos():
    if _use_supabase():
        try:
            return _sb_get("gastos", order="fecha.desc") or []
        except Exception:
            return []
    conn = get_conn()
    try:
        return [dict(x) for x in conn.execute("SELECT * FROM gastos ORDER BY fecha DESC").fetchall()]
    finally:
        conn.close()


def save_gasto(data: dict, gasto_id=None):
    payload = {k: data.get(k) for k in ["fecha", "modulo", "concepto", "monto", "notas"]}
    if _use_supabase():
        if gasto_id:
            _sb_update("gastos", payload, "id", gasto_id)
            return gasto_id
        else:
            return _sb_insert("gastos", payload)
    else:
        conn = get_conn()
        try:
            if gasto_id:
                conn.execute("UPDATE gastos SET fecha=?,modulo=?,concepto=?,monto=?,notas=? WHERE id=?",
                    (*payload.values(), gasto_id))
                conn.commit()
                return gasto_id
            else:
                cur = conn.execute("INSERT INTO gastos (fecha,modulo,concepto,monto,notas) VALUES (?,?,?,?,?)",
                    tuple(payload.values()))
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()


def delete_gasto(gasto_id):
    if _use_supabase():
        _sb_delete("gastos", "id", gasto_id)
    else:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM gastos WHERE id=?", (gasto_id,)); conn.commit()
        finally:
            conn.close()


init_db()
