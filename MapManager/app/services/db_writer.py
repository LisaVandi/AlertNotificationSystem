import json
import logging
import psycopg2

from MapViewer.app.config.settings import DATABASE_CONFIG

logger = logging.getLogger(__name__)

def update_node_evacuation_path(node_id: int, arc_path: list[int]):
    """
    Aggiorna il campo evacuation_path del nodo nel database,
    salvando una lista ordinata di arc_id.

    Args:
        node_id (int): ID del nodo da aggiornare
        arc_path (list[int]): Lista ordinata di arc_id
    """
    if not arc_path:
        logger.warning(f"Nessun percorso da salvare per il nodo {node_id}")
        return

    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()

        # Salva come stringa JSON
        json_path = json.dumps(arc_path)

        cur.execute("""
            UPDATE nodes
            SET evacuation_path = %s
            WHERE node_id = %s
        """, (json_path, node_id))

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Evacuation path (arc_id) salvato per il nodo {node_id}")

    except Exception as e:
        logger.error(f"Errore aggiornando evacuation_path per nodo {node_id}: {str(e)}")
        raise
