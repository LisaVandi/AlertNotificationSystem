import psycopg2
from typing import List
from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.config.logging import setup_logging

logger = setup_logging("db_reader", "MapManager/logs/dbReader.log")

def get_arc_final_node(arc_id: int) -> int | None:
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT final_node FROM arcs WHERE arc_id = %s", (arc_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error retrieving final_node for arc {arc_id}: {e}")
        return None

def get_all_node_ids() -> List[int]:
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT node_id FROM nodes")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Error get_all_node_ids: {e}")
        return []

def get_node_ids_by_type(node_type: str) -> List[int]:
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT node_id FROM nodes WHERE node_type = %s", (node_type,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Error get_node_ids_by_type({node_type}): {e}")
        return []

def get_node_ids_by_floor(floor_level: int) -> List[int]:
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT node_id FROM nodes WHERE %s = ANY(floor_level)", (floor_level,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Error get_node_ids_by_floor({floor_level}): {e}")
        return []

def get_node_ids_in_zone(x1: float, x2: float, y1: float, y2: float, z1: int, z2: int) -> List[int]:
    """
    Restituisce gli ID dei nodi il cui centro ( (x1+x2)/2, (y1+y2)/2 ) ricade nel box [x1,x2]x[y1,y2]
    e il cui floor_level contiene almeno un piano in [z1, z2].
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT node_id, x1, x2, y1, y2, floor_level
            FROM nodes
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        res: List[int] = []
        for node_id, nx1, nx2, ny1, ny2, floors in rows:
            cx = (nx1 + nx2) / 2.0
            cy = (ny1 + ny2) / 2.0
            in_xy = (x1 <= cx <= x2) and (y1 <= cy <= y2)
            floors_list = floors if isinstance(floors, list) else [floors]
            in_z = any(z1 <= f <= z2 for f in floors_list)
            if in_xy and in_z:
                res.append(node_id)
        return res
    except Exception as e:
        logger.error(f"Error get_node_ids_in_zone: {e}")
        return []
