from typing import List
import yaml
import psycopg2
import os
from pathlib import Path

from MapManager.app.services.db_reader import get_arc_final_node
from MapManager.app.services.path_calculator import find_shortest_path_to_exit
from MapManager.app.services.db_writer import update_node_evacuation_path
from MapManager.app.config.logging import setup_logging
from MapViewer.app.services.graph_manager import graph_manager
from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.services.publisher import publish_paths_ready
from NotificationCenter.app.config.settings import ACK_EVACUATION_QUEUE

logger = setup_logging("evacuation_manager", "MapManager/logs/evacuationManager.log")

CONFIG_PATH = "PositionManager/config/config.yaml"
with open(CONFIG_PATH, "r") as f:
    emergency_config = yaml.safe_load(f)
logger.info(f"Loaded emergency types: {list(emergency_config.get('emergencies', {}).keys())}")

outdoor_events = {"Earthquake", "Hazardous Material", "Severe Weather", "Power Outage"}

def initialize_evacuation_paths(floor_level: int, event_type: str):
    logger.info(f"Initializing evacuation paths for floor {floor_level} with event {event_type}")

    G = graph_manager.get_graph(floor_level)
    if G is None:
        logger.warning(f"No graph loaded for floor {floor_level}")
        return

    safe_nodes = get_safe_nodes_for_event(G, event_type)
    if not safe_nodes:
        logger.warning(f"No safe nodes found for initialization on floor {floor_level} with event {event_type}")
        return

    for node_id, data in G.nodes(data=True):
        if event_type in outdoor_events and data.get("node_type") == "outdoor":
            update_node_evacuation_path(node_id, [])
            logger.info(f"Node {node_id} is already outdoor; no path needed.")
            continue
        
        if event_type == "Flood" and data.get("node_type") == "stairs" and data.get("floor_level") == 0:
            update_node_evacuation_path(node_id, [])
            logger.info(f"Node {node_id} is already stairs at floor 0; no path needed.")
            continue
        
        if event_type == "Fire":
            cfg = emergency_config["emergencies"]["Fire"]["danger_zone"]
            # if the node is already outside the danger zone, skip
            if not (cfg["x1"] <= data["x"] <= cfg["x2"]
                    and cfg["y1"] <= data["y"] <= cfg["y2"]
                    and cfg["z1"] <= data["floor_level"] <= cfg["z2"]):
                update_node_evacuation_path(node_id, [])
                logger.info(f"Node {node_id} is already outside fire zone; skipping.")
                continue

        
        path = find_shortest_path_to_exit(G, node_id, safe_nodes)
        if path is None:
            logger.warning(f"[Init] No path (None) for node {node_id}; skipping")
        else:
            update_node_evacuation_path(node_id, [path[0]])
            logger.info(f"[Init] Saved evacuation path for node {node_id}: {path[0]}")


def get_safe_nodes_for_event(G, event_type: str) -> List[int]:
    logger.debug(f"Selecting safe nodes for event '{event_type}'")

    if event_type == "Flood":
        safe = [n for n, d in G.nodes(data=True) if d.get("node_type") == "stairs" and d.get("floor_level") == 0]
        logger.info(f"(Flood) Safe nodes (stairs): {safe}")
        return safe

    if event_type in outdoor_events:
        safe = [n for n, d in G.nodes(data=True) if d.get("node_type") == "outdoor"]
        logger.info(f"({event_type}) Safe nodes (outdoor): {safe}")
        return safe

    # Fire: danger zone
    if event_type == "Fire":
        cfg = emergency_config["emergencies"]["Fire"]["danger_zone"]
        x1, x2 = cfg["x1"], cfg["x2"]
        y1, y2 = cfg["y1"], cfg["y2"]
        z1, z2 = cfg["z1"], cfg["z2"]
        safe = []
        for n, d in G.nodes(data=True):
            xc, yc, zf = d.get("x"), d.get("y"), d.get("floor_level")
            if xc is None or yc is None or zf is None:
                continue
            if not (x1 <= xc <= x2 and y1 <= yc <= y2 and z1 <= zf <= z2):
                safe.append(n)
        logger.info(f"(Fire) Safe nodes outside danger zone: {safe}")
        return safe

def get_saved_evacuation_path(node_id: int) -> List[int]:
    """
    Reads from the DB the list of arc_ids representing the evacuation path
    already saved for the specified node.
    """
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT evacuation_path FROM nodes WHERE node_id = %s", (node_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result and result[0]:
            return result[0]  
        return []
    except Exception as e:
        logger.error(f"Error fetching saved evacuation path for node {node_id}: {e}")
        return []
    
def handle_evacuations(floor_level: int, alert_nodes: List[int], event_type:str, rabbitmq_handler=None):
    try:
        if event_type not in ("Flood", "Earthquake", "Hazardous Material", "Severe Weather", "Power Outage", "Fire"):
            logger.error(f"Invalid event_type '{event_type}'")
            return
        logger.info(f"Handling evacuation for floor={floor_level}, nodes={alert_nodes}, event={event_type}")
        
        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"No graph loaded for floor {floor_level}")
            return

        safe_nodes = get_safe_nodes_for_event(G, event_type)
        if not safe_nodes:
            logger.warning(f"No safe nodes for floor {floor_level}, event {event_type}")
            return

        logger.debug(f"Computed safe_nodes={safe_nodes}")
        # raccogliamo tutti i percorsi in un dict nodo→lista_arc
        paths_by_node: dict[int, list[int]] = {}
        for source in alert_nodes:
            if source in safe_nodes:
                update_node_evacuation_path(source, [])
                paths_by_node[source] = []
                continue

            if source not in G:
                logger.warning(f"Alert node {source} not in graph")
                continue
            
            node_data = G.nodes[source]
            if event_type in outdoor_events and node_data.get("node_type") == "outdoor":
                update_node_evacuation_path(source, [])
                logger.info(f"Node {source} is already outdoor; skipping path calculation.")
                continue
            
            if event_type == "Flood" and node_data.get("node_type") == "stairs" and node_data.get("floor_level") == 0:
                update_node_evacuation_path(source, [])
                logger.info(f"Node {source} is already stairs at floor 0; no path needed.")
                continue

            if event_type == "Fire": 
                cfg = emergency_config["emergencies"]["Fire"]["danger_zone"]
                # if the alert node is already outside the danger zone, do not calculate or save anything
                if not (cfg["x1"] <= node_data["x"] <= cfg["x2"]
                        and cfg["y1"] <= node_data["y"] <= cfg["y2"]
                        and cfg["z1"] <= node_data["floor_level"] <= cfg["z2"]):
                    update_node_evacuation_path(source, [])
                    logger.info(f"Node {source} is outside fire zone; skipping.")
                    continue

            path_saved = get_saved_evacuation_path(source)
            if path_saved:
                last_arc = path_saved[-1]
                final_node = get_arc_final_node(last_arc)
                if final_node is None:
                    logger.warning(f"No final_node found for arc {last_arc}; recalculating anyway.")
                elif source == final_node:
                    logger.info(f"User at node {source} has already reached evacuation end; skipping recalculation.")
                    continue

            # Otherwise, calculate the shortest path
            path = find_shortest_path_to_exit(G, source, safe_nodes)
            if path is None:
                logger.warning(f"No evacuation path found for node {source}; skipping DB update")
            else:
                update_node_evacuation_path(source, path)
                paths_by_node[source] = path
                logger.info(f"Saved evacuation path for node {source}: {path}")
                
        # publish payload with all paths for each node
        if rabbitmq_handler:
            try:
                publish_paths_ready(rabbitmq_handler)
                logger.info(f"Published 'paths_ready' su {ACK_EVACUATION_QUEUE}")
            except Exception as e:
                logger.error(f"Error sending 'paths_ready' message: {e}")
                    
    except Exception as e:
        logger.error(f"Error in handle_evacuations: {e}")
        raise
    
