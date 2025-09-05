import psycopg2
from typing import Iterable, List
from MapViewer.app.config.settings import DATABASE_CONFIG  
from MapManager.app.config.logging import setup_logging

logger = setup_logging("db_writer", "MapManager/logs/dbWriter.log")

def _get_conn():
    return psycopg2.connect(**DATABASE_CONFIG)

def update_node_evacuation_path(node_id: int, arc_path: List[int]):
    """
    Salva su nodes.evacuation_path (int[]) la lista ordinata di arc_id per il nodo dato.
    """
    arc_path_clean = [int(a) for a in (arc_path or []) if a is not None]
    sql = "UPDATE nodes SET evacuation_path = %s WHERE node_id = %s"
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (arc_path_clean, node_id))
            conn.commit()
        logger.info(f"Saved evacuation path for node {node_id}: {arc_path_clean}")
    except Exception as e:
        logger.error(f"Error updating evacuation_path for node {node_id}: {str(e)}")
        raise

def bulk_update_node_evacuation_paths(pairs: List[tuple[int, List[int]]]):
    if not pairs: return 0
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            for node_id, arc_path in pairs:
                cur.execute(
                    "UPDATE nodes SET evacuation_path=%s WHERE node_id=%s",
                    (arc_path or None, node_id)
                )
            conn.commit()
        logger.info(f"Saved {len(pairs)} evacuation paths.")
        return len(pairs)
    except Exception as e:
        logger.error(f"bulk_update_node_evacuation_paths error: {e}")
        raise

def set_all_safe(safe: bool = True) -> int:
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE nodes SET safe = %s", (safe,))
            n = cur.rowcount
            conn.commit()
        logger.info(f"set_all_safe({safe}) -> {n} rows")
        return n
    except Exception as e:
        logger.error(f"set_all_safe error: {e}")
        raise

def set_nodes_safe(node_ids: Iterable[int], safe: bool) -> int:
    ids = list(node_ids)
    if not ids:
        logger.info("set_nodes_safe: empty ids, nothing to do")
        return 0
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE nodes SET safe=%s WHERE node_id = ANY(%s)", (safe, ids))
            n = cur.rowcount
            conn.commit()
        logger.info(f"set_nodes_safe(len={len(ids)}, safe={safe}) -> {n}")
        return n
    except Exception as e:
        logger.error(f"set_nodes_safe error: {e}")
        raise

def set_safe_by_floor(floor_level: int, safe: bool) -> int:
    try:
        with _get_conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE nodes SET safe=%s WHERE %s = ANY(floor_level)", (safe, floor_level))
            n = cur.rowcount
            conn.commit()
        logger.info(f"set_safe_by_floor(floor={floor_level}, safe={safe}) -> {n}")
        return n
    except Exception as e:
        logger.error(f"set_safe_by_floor error: {e}")
        raise
