import psycopg2

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
