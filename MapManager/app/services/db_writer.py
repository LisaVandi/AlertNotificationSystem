import psycopg2

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.app.config.logging import setup_logging

logger = setup_logging("db_writer", "MapViewer/logs/dbWriter.log")

def update_node_evacuation_path(node_id: int, arc_path: list[int]):
    """
    Update the evacuation_path field in the nodes table for the specified node.
    Saves the ordered list of arc IDs representing the evacuation path.

    Args:
        node_id (int): Node identifier to update.
        arc_path (list[int]): Ordered list of arc IDs forming the evacuation path.
    """
    if not arc_path:
        arc_path = []
        logger.warning(f"No evacuation path to save for node {node_id}")
    
    arc_path_clean = [int(a) for a in arc_path if a is not None]

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            UPDATE nodes
            SET evacuation_path = %s
            WHERE node_id = %s
        """, (arc_path_clean, node_id))

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Saved evacuation path for node {node_id}: {arc_path_clean}")

    except Exception as e:
        logger.error(f"Error updating evacuation_path for node {node_id}: {str(e)}")
        raise
