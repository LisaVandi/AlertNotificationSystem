import psycopg2
from typing import List

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.app.services.graph_manager import graph_manager

from MapManager.app.config.logging import setup_logging

logger = setup_logging("arc_updater", "MapManager/logs/arcUpdater.log")

def update_arc_statuses(floor_level: int, broken_arc_ids: List[int] = []):
    G = graph_manager.get_graph(floor_level)
    if G is None:
        logger.warning(f"No graph for floor {floor_level}")
        return
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        for _, _, data in G.edges(data=True):
            arc_id = data.get("arc_id")
            if arc_id is None: continue
            is_broken = arc_id in broken_arc_ids
            currently_active = data.get("active", True)
            if currently_active and is_broken:
                logger.info(f"Deactivating arc {arc_id} (broken)")
                data["active"] = False
                cur.execute("UPDATE arcs SET active = FALSE WHERE arc_id = %s", (arc_id,))
                cur.execute("""
                    INSERT INTO arc_status_log (arc_id, previous_state, new_state, modified_by)
                    VALUES (%s, %s, %s, %s)
                """, (arc_id, True, False, 'MapManager'))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating arcs: {str(e)}")
        raise
