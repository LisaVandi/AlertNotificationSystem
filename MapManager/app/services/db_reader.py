# db_reader.py
# -------------------------------------------------------------
# Data Access Layer per tabelle 'nodes' e 'arcs'
# - Connessione sicura via context manager
# - Tipi e docstring consistenti
# - Nessuna funzione duplicata
# - Query parametriche e gestione array floor_level
# -------------------------------------------------------------

from __future__ import annotations

from typing import List, Dict, Iterable, Optional, Tuple
import psycopg2
import psycopg2.extras as pg_extras

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.config.logging import setup_logging

logger = setup_logging("db_reader", "MapManager/logs/dbReader.log")


# -----------------------------
# Helpers
# -----------------------------

def _get_conn():
    """
    Ritorna una nuova connessione psycopg2 usando DATABASE_CONFIG.
    """
    # Nota: rely on autocommit=False di default; i SELECT non richiedono commit.
    return psycopg2.connect(**DATABASE_CONFIG)


def _as_list(value) -> List[int]:
    """
    Converte un singolo intero o una lista in List[int].
    Gestisce anche None.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [int(v) for v in value if v is not None]
    return [int(value)]


def _center(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return (float(a) + float(b)) / 2.0


# -----------------------------
# Letture su ARCS
# -----------------------------

def get_arc_final_node(arc_id: int) -> Optional[int]:
    """
    Ritorna il nodo finale (final_node) dell'arco dato, oppure None se non trovato.
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT final_node FROM arcs WHERE arc_id = %s", (arc_id,))
            row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    except Exception as e:
        logger.error(f"Error get_arc_final_node({arc_id}): {e}", exc_info=True)
        return None


def get_intra_floor_arcs(floor_level: int) -> List[Dict]:
    """
    Ritorna gli archi interni al piano 'floor_level'.
    Criterio: entrambi i nodi estremi dell'arco hanno 'floor_level' che include il piano dato.

    Output: List[Dict] con chiavi:
      - arc_id: int
      - initial_node_id: int
      - final_node_id: int
      - active: bool
    """
    sql = """
        SELECT a.arc_id,
               a.initial_node,
               a.final_node,
               a.active
        FROM arcs a
        JOIN nodes n1 ON n1.node_id = a.initial_node
        JOIN nodes n2 ON n2.node_id = a.final_node
        WHERE %s = ANY(n1.floor_level)
          AND %s = ANY(n2.floor_level)
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (floor_level, floor_level))
            rows = cur.fetchall()
        out: List[Dict] = []
        for arc_id, ini, fin, active in rows:
            out.append({
                "arc_id": int(arc_id),
                "initial_node_id": int(ini),
                "final_node_id": int(fin),
                "active": bool(active),
            })
        return out
    except Exception as e:
        logger.error(f"Error get_intra_floor_arcs(floor={floor_level}): {e}", exc_info=True)
        return []


def get_interfloor_stair_arcs() -> List[Dict]:
    """
    Ritorna gli archi che connettono nodi di 'tipo scala' (inter-floor).
    Non imponiamo un vincolo su 'arc_type' perché lo schema può variare.
    Se almeno uno dei due estremi è di tipo 'stair', consideriamo l'arco candidato
    per collegare piani differenti (la distinzione f1!=f2 verrà poi costruita dai consumer
    usando gli attributi dei nodi).

    Output: List[Dict] con chiavi:
      - arc_id: int
      - initial_node_id: int
      - final_node_id: int
      - active: bool
    """
    sql = """
        SELECT a.arc_id,
               a.initial_node,
               a.final_node,
               a.active,
               a.traversal_time
        FROM arcs a
        JOIN nodes n1 ON n1.node_id = a.initial_node
        JOIN nodes n2 ON n2.node_id = a.final_node
        WHERE (n1.node_type = 'stairs' OR n2.node_type = 'stairs')
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        out: List[Dict] = []
        for arc_id, ini, fin, active, ttime in rows:
            out.append({
                "arc_id": int(arc_id),
                "initial_node_id": int(ini),
                "final_node_id": int(fin),
                "active": bool(active),
                "traversal_time": ttime
            })
        return out
    except Exception as e:
        logger.error(f"get_interfloor_stair_arcs error: {e}", exc_info=True)
        return []


# -----------------------------
# Letture su NODES
# -----------------------------

def get_nodes_on_floor(floor_level: int) -> List[int]:
    """
    Ritorna gli ID dei nodi presenti (anche) al piano indicato.
    """
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT node_id FROM nodes WHERE %s = ANY(floor_level)", (floor_level,))
            rows = cur.fetchall()
        return [int(r[0]) for r in rows]
    except Exception as e:
        logger.error(f"Error get_nodes_on_floor({floor_level}): {e}", exc_info=True)
        return []


def get_node_ids_by_floor(floor_level: int) -> List[int]:
    return get_nodes_on_floor(floor_level)


def get_node_ids_by_type(node_type: str) -> List[int]:
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT node_id FROM nodes WHERE node_type = %s", (node_type,))
            rows = cur.fetchall()
        return [int(r[0]) for r in rows]
    except Exception as e:
        logger.error(f"Error get_node_ids_by_type({node_type}): {e}", exc_info=True)
        return []


def get_node_ids_in_zone(x1: float, x2: float, y1: float, y2: float, z1: int, z2: int) -> List[int]:
    """
    Ritorna gli ID dei nodi la cui proiezione 2D (centro dell'area [x1,x2]x[y1,y2]) cade nel box:
      x in [min(x1,x2), max(x1,x2)] e y in [min(y1,y2), max(y1,y2)]
    e per cui almeno un piano in floor_level è nell'intervallo [min(z1,z2), max(z1,z2)].

    Nota: per semplicità calcoliamo il centro come media degli estremi (x1,x2,y1,y2) su tabella 'nodes'.
    """
    # Normalizza i range
    xlo, xhi = (x1, x2) if x1 <= x2 else (x2, x1)
    ylo, yhi = (y1, y2) if y1 <= y2 else (y2, y1)
    zlo, zhi = (z1, z2) if z1 <= z2 else (z2, z1)

    # Se vuoi spostare il filtro nel DB usa un'espressione sul centro; qui teniamo semplice e robusto.
    sql = """
        SELECT node_id, x1, x2, y1, y2, floor_level
        FROM nodes
    """
    try:
        ids: List[int] = []
        with _get_conn() as conn, conn.cursor(cursor_factory=pg_extras.DictCursor) as cur:
            cur.execute(sql)
            for row in cur.fetchall():
                nid = int(row["node_id"])
                cx = _center(row["x1"], row["x2"])
                cy = _center(row["y1"], row["y2"])
                floors = _as_list(row["floor_level"])

                if cx is None or cy is None:
                    continue
                if not (xlo <= cx <= xhi and ylo <= cy <= yhi):
                    continue
                if not any(zlo <= int(f) <= zhi for f in floors):
                    continue

                ids.append(nid)
        return ids
    except Exception as e:
        logger.error(f"Error get_node_ids_in_zone([{x1},{x2}]x[{y1},{y2}] z[{z1},{z2}]): {e}", exc_info=True)
        return []


def get_node_attributes(node_ids: Iterable[int]) -> Dict[int, Dict]:
    """
    Ritorna attributi per i node_id richiesti.

    Output: Dict[node_id] = {
        "x": float | None,           # centro X (media x1,x2)
        "y": float | None,           # centro Y (media y1,y2)
        "node_type": str | None,
        "floor_level": List[int]
    }
    """
    node_ids = [int(n) for n in (node_ids or [])]
    if not node_ids:
        return {}

    sql = """
        SELECT node_id, x1, x2, y1, y2, node_type, floor_level
        FROM nodes
        WHERE node_id = ANY(%s)
    """
    try:
        with _get_conn() as conn, conn.cursor(cursor_factory=pg_extras.DictCursor) as cur:
            cur.execute(sql, (node_ids,))
            rows = cur.fetchall()

        out: Dict[int, Dict] = {}
        for row in rows:
            nid = int(row["node_id"])
            cx = _center(row["x1"], row["x2"])
            cy = _center(row["y1"], row["y2"])
            ntype = row.get("node_type") if isinstance(row, dict) else row[5]
            floors = _as_list(row["floor_level"])
            out[nid] = {
                "x": cx,
                "y": cy,
                "node_type": ntype,
                "floor_level": floors,
            }
        return out
    except Exception as e:
        logger.error(f"get_node_attributes error: {e}", exc_info=True)
        return {}


# -----------------------------
# Varianti utili / bulk
# -----------------------------

def get_nodes_on_floors(floor_levels: Iterable[int]) -> Dict[int, List[int]]:
    """
    Ritorna una mappa { floor_level: [node_id, ...] } per i piani richiesti.
    """
    floors = sorted({int(f) for f in (floor_levels or [])})
    if not floors:
        return {}

    sql = """
        SELECT node_id, floor_level
        FROM nodes
        WHERE EXISTS (
            SELECT 1 FROM unnest(%s::int[]) f WHERE f = ANY(nodes.floor_level)
        )
    """
    try:
        result: Dict[int, List[int]] = {f: [] for f in floors}
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (floors,))
            for node_id, fl_arr in cur.fetchall():
                fls = _as_list(fl_arr)
                for f in fls:
                    if f in result:
                        result[f].append(int(node_id))
        return result
    except Exception as e:
        logger.error(f"Error get_nodes_on_floors({floors}): {e}", exc_info=True)
        return {}


def get_floor_levels_for_nodes(node_ids: Iterable[int]) -> Dict[int, List[int]]:
    """
    Ritorna { node_id: [floor_levels...] } per un insieme di nodi.
    Utile per evitare N+1 query.
    """
    node_ids = [int(n) for n in (node_ids or [])]
    if not node_ids:
        return {}

    sql = "SELECT node_id, floor_level FROM nodes WHERE node_id = ANY(%s)"
    try:
        out: Dict[int, List[int]] = {}
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (node_ids,))
            for nid, fl in cur.fetchall():
                out[int(nid)] = _as_list(fl)
        return out
    except Exception as e:
        logger.error(f"Error get_floor_levels_for_nodes({len(node_ids)} ids): {e}", exc_info=True)
        return {}
