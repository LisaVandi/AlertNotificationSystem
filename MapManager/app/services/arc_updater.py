import logging
import psycopg2
from typing import List

from MapManager.app.config.settings import DATABASE_CONFIG, PATHFINDING_CONFIG
from MapViewer.app.services.graph_manager import graph_manager

logger = logging.getLogger(__name__)

def update_arc_statuses(floor_level: int, broken_arc_ids: List[int] = []):
    """
    Aggiorna lo stato di attivazione degli archi nel grafo e nel DB:
    - disattiva archi interrotti (lista)
    - disattiva archi sovraccarichi (flow > capacity)

    Args:
        floor_level (int): piano da aggiornare
        broken_arc_ids (List[int]): lista opzionale di arc_id interrotti
    """
    G = graph_manager.get_graph(floor_level)
    if G is None:
        logger.warning(f"Nessun grafo per il piano {floor_level}")
        return

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()

        for u, v, data in G.edges(data=True):
            arc_id = data.get("arc_id")
            if arc_id is None:
                continue

            flow = data.get("flow", 0)
            capacity = data.get("capacity", PATHFINDING_CONFIG["max_arc_capacity"])
            is_broken = arc_id in broken_arc_ids
            is_overloaded = flow > capacity

            should_deactivate = is_broken or is_overloaded
            currently_active = data.get("active", True)

            if currently_active and should_deactivate:
                logger.info(f"Deactivating arc {arc_id} (broken={is_broken}, overloaded={is_overloaded})")

                data["active"] = False

                cur.execute("""
                    UPDATE arcs SET active = FALSE WHERE arc_id = %s
                """, (arc_id,))

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
