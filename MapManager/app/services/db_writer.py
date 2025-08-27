import psycopg2
from typing import List, Optional

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.config.logging import setup_logging


logger = setup_logging("db_writer", "MapManager/logs/dbWriter.log")

def update_node_evacuation_path(node_id: int, arc_path: list[int]):
    """
    Update the evacuation_path field in the nodes table for the specified node.
    Saves the ordered list of arc IDs representing the evacuation path.

    Args:
        node_id (int): Node identifier to update.
        arc_path (list[int]): Ordered list of arc IDs forming the evacuation path.
    """
    
    arc_path_clean = [int(a) for a in arc_path if a is not None]
    next_arc = arc_path_clean[0] if arc_path_clean else None

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            UPDATE nodes
            SET evacuation_path = %s,
                last_modified = NOW(),
                last_modified_by = %s
            WHERE node_id = %s
        """, (
            [next_arc] if next_arc is not None else None, 
            'MapManager',
            node_id
        ))

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Saved evacuation path for node {node_id}: {arc_path_clean}")

    except Exception as e:
        logger.error(f"Error updating evacuation_path for node {node_id}: {str(e)}")
        raise

def set_all_safe(safe: bool) -> int:
    """
    Imposta il flag 'safe' per TUTTI i nodi.
    Ritorna il numero di righe aggiornate.
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("UPDATE nodes SET safe = %s", (safe,))
        rowcount = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"set_all_safe({safe}) -> updated {rowcount} nodes")
        return rowcount
    except Exception as e:
        logger.error(f"set_all_safe error: {e}")
        raise


def set_nodes_safe(node_ids: List[int], safe: bool) -> int:
    """
    Imposta il flag 'safe' per una lista di node_id.
    """
    if not node_ids:
        logger.info("set_nodes_safe: empty node_ids, nothing to do")
        return 0

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "UPDATE nodes SET safe = %s WHERE node_id = ANY(%s)",
            (safe, node_ids)
        )
        rowcount = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"set_nodes_safe(ids={node_ids}, safe={safe}) -> {rowcount} updated")
        return rowcount
    except Exception as e:
        logger.error(f"set_nodes_safe error: {e}")
        raise


def set_safe_by_floor(floor_level: int, safe: bool) -> int:
    """
    Imposta 'safe' per tutti i nodi che hanno 'floor_level' contenente il piano indicato.
    Nota: floor_level è un array in DB (es. nodi scala su più piani).
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        # '%s = ANY(floor_level)' funziona con array INT in Postgres
        cur.execute(
            "UPDATE nodes SET safe = %s WHERE %s = ANY(floor_level)",
            (safe, floor_level)
        )
        rowcount = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"set_safe_by_floor(floor={floor_level}, safe={safe}) -> {rowcount} updated")
        return rowcount
    except Exception as e:
        logger.error(f"set_safe_by_floor error: {e}")
        raise
