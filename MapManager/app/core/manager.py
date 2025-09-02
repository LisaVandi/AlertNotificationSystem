from typing import List
import psycopg2, yaml

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.app.services.graph_manager import graph_manager

from MapManager.app.config.logging import setup_logging
from MapManager.app.services.db_reader import get_arc_final_node
from MapManager.app.services.path_calculator import find_shortest_path_to_exit
from MapManager.app.services.db_writer import update_node_evacuation_path
from MapManager.app.services.publisher import publish_paths_ready
from MapManager.app.config.settings import ACK_EVACUATION_QUEUE, ALERTS_CONFIG_PATH, PATHFINDING_CONFIG

logger = setup_logging("evacuation_manager", "MapManager/logs/evacuationManager.log")

try:
    with open(ALERTS_CONFIG_PATH, "r", encoding="utf-8") as f:
        emergency_config = yaml.safe_load(f) or {}
    logger.info(f"Loaded emergency types: {list(emergency_config.get('emergencies', {}).keys())}")
except Exception as e:
    logger.error(f"Cannot load emergency config at {ALERTS_CONFIG_PATH}: {e}")
    emergency_config = {"emergencies": {}}

def get_safe_nodes_for_event(G, event_type: str) -> List[int]:
    """
    Target di evacuazione derivati da alerts.yaml (emergencies):
    - type=all   → tutti i nodi con node_type == safe_node_type
    - type=floor → node_type == safe_node_type e almeno un piano ∈ danger_floors
    - type=zone  → target = safe_node_type (la zona serve per marcare unsafe i nodi, non per i target)
    """
    emergencies = emergency_config.get("emergencies", {})
    rule = emergencies.get(event_type)
    if not rule:
        logger.warning(f"Nessuna regola YAML per event='{event_type}'")
        return []

    etype = rule.get("type")
    safe_node_type = rule.get("safe_node_type")
    if not safe_node_type:
        logger.warning(f"Nessun 'safe_node_type' per event='{event_type}'")
        return []

    if etype == "all":
        safe = [n for n, d in G.nodes(data=True) if d.get("node_type") == safe_node_type]
        logger.info(f"({event_type}) Target nodes ({safe_node_type}): {safe}")
        return safe

    if etype == "floor":
        wanted = set(rule.get("danger_floors") or [])
        def flist(v): return v if isinstance(v, list) else [v]
        safe = [n for n, d in G.nodes(data=True)
                if d.get("node_type") == safe_node_type
                and any(f in wanted for f in flist(d.get("floor_level")))]
        logger.info(f"({event_type}) Target nodes ({safe_node_type}@{sorted(wanted)}): {safe}")
        return safe

    if etype == "zone":
        safe = [n for n, d in G.nodes(data=True) if d.get("node_type") == safe_node_type]
        logger.info(f"({event_type}) Target nodes ({safe_node_type}): {safe}")
        return safe

    logger.warning(f"Tipo regola non gestito: '{etype}' per event='{event_type}'")
    return []

def initialize_evacuation_paths(floor_level: int):
    """
    Inizializza gli evacuation_path per i nodi del piano:
    - se un nodo è già un target (es. è 'outdoor' per Earthquake, o 'stairs@0' per Flood), path = []
      altrimenti lascia invariato (verrà ricalcolato quando arrivano i nodi pericolosi dal PositionManager).
    """
    try:
        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"Nessun grafo per il piano {floor_level}")
            return
        
        exit_types = PATHFINDING_CONFIG.get("default_exit_node_types", [])
        if not exit_types:
            logger.info("Nessun default_exit_node_types configurato: init neutra saltata.")
            return

        count = 0
        for n, d in G.nodes(data=True):
            if d.get("node_type") in exit_types:
                update_node_evacuation_path(n, [])  # i target non hanno bisogno di path
                count += 1

        logger.info(f"Init neutra su piano {floor_level}: azzerati {count} target (types={exit_types})")


        # target_nodes = set(get_safe_nodes_for_event(G, event_type))
        # if not target_nodes:
        #     logger.info(f"Nessun target per init su piano {floor_level} (evento {event_type})")
        #     return

        # for n, d in G.nodes(data=True):
        #     is_target = n in target_nodes
        #     if is_target:
        #         update_node_evacuation_path(n, [])
        # logger.info(f"Init evacuation_path su piano {floor_level}: azzerati {len(target_nodes)} target")

    except Exception as e:
        logger.error(f"Errore initialize_evacuation_paths: {e}")


def get_saved_evacuation_path(node_id: int) -> List[int]:
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT evacuation_path FROM nodes WHERE node_id = %s", (node_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row and row[0] else []
    except Exception as e:
        logger.error(f"Errore leggendo evacuation_path per nodo {node_id}: {e}")
        return []

def handle_evacuations(floor_level: int, alert_nodes: List[int], event_type: str, rabbitmq_handler=None):
    try:
        if not alert_nodes:
            return

        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"Nessun grafo per il piano {floor_level}")
            return

        safe_nodes = get_safe_nodes_for_event(G, event_type)
        if not safe_nodes:
            logger.warning(f"Nessun nodo target per event={event_type} sul piano {floor_level}")
            return

        paths_by_node: dict[int, list[int]] = {}
        safe_nodes_set = set(safe_nodes)
        for source in alert_nodes:
            if source not in G:
                logger.warning(f"Nodo di alert {source} non presente nel grafo")
                continue

            # Se il nodo è già "target", nessun path necessario
            if source in safe_nodes_set:
                update_node_evacuation_path(source, [])
                continue

            # Se ho un path già salvato e l’ultimo arco porta al nodo corrente, salto
            saved = get_saved_evacuation_path(source)
            if saved:
                last_arc = saved[-1]
                final_node = get_arc_final_node(last_arc)
                # if final_node is not None and final_node == source:
                #     logger.info(f"Nodo {source} sembra essere già a destinazione, skip.")
                #     continue
                if final_node is not None and final_node in safe_nodes_set:
                    logger.info(f"Nodo {source} ha già un path verso un target (last_arc termina in target). Skip.")
                    continue

            path = find_shortest_path_to_exit(G, source, safe_nodes)
            if path is None:
                logger.warning(f"Nessun path di evacuazione per nodo {source}")
                continue

            update_node_evacuation_path(source, path)
            paths_by_node[source] = path

        if rabbitmq_handler:
            try:
                publish_paths_ready(rabbitmq_handler)
                logger.info(f"Inviato 'paths_ready' su {ACK_EVACUATION_QUEUE}")
            except Exception as e:
                logger.error(f"Errore pubblicando paths_ready: {e}")

    except Exception as e:
        logger.error(f"Errore in handle_evacuations: {e}")
        raise
