import psycopg2
from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.config.logging import setup_logging

logger = setup_logging("db_reader", "MapManager/logs/dbReader.log")

def get_arc_final_node(arc_id: int) -> int | None:
    """
    Returns the final_node corresponding to the given arc_id, or None if it does not exist.
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "SELECT final_node FROM arcs WHERE arc_id = %s",
            (arc_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None

    except Exception as e:
        logger.error(f"Error retrieving final_node for arc {arc_id}: {e}")
        return None
