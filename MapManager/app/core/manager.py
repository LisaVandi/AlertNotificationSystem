from typing import List, Optional
import yaml

from MapManager.app.config.settings import PATHFINDING_CONFIG
from MapManager.app.services.path_calculator import find_shortest_path_to_exit
from MapViewer.app.services.graph_manager import graph_manager
from MapManager.app.services.db_writer import update_node_evacuation_path
from MapManager.app.config.logging import setup_logging

logger = setup_logging("evacuation_manager", "MapManager/logs/evacuationManager.log")

CONFIG_PATH = "PositionManager/config/config.yaml"
with open(CONFIG_PATH, "r") as f:
    emergency_config = yaml.safe_load(f)
logger.info(f"Loaded emergency types: {list(emergency_config.get('emergencies', {}).keys())}")

def initialize_evacuation_paths(floor_level: int, default_event_type: str = "Evacuation"):
    """
    Calcola e salva i percorsi di evacuazione per TUTTI i nodi del piano, 
    usando come event_type il default_event_type se non ne viene passato uno.
    """
    logger.info(f"Initializing evacuation paths for floor {floor_level} with event {default_event_type}")

    G = graph_manager.get_graph(floor_level)
    if G is None:
        logger.warning(f"No graph loaded for floor {floor_level}")
        return

    safe_nodes = get_safe_nodes_for_event(G, default_event_type)
    if not safe_nodes:
        logger.warning(f"No safe nodes found for initialization on floor {floor_level} with event {default_event_type}")
        return

    for node_id in G.nodes():
        path = find_shortest_path_to_exit(G, node_id, safe_nodes)
        if path is None:
            logger.warning(f"[Init] No path (None) for node {node_id}; skipping")
        else:
            update_node_evacuation_path(node_id, path)
            logger.info(f"[Init] Saved evacuation path for node {node_id}: {path}")


def get_safe_nodes_for_event(G, event_type: str) -> List[int]:
    logger.debug(f"Selecting safe nodes for event '{event_type}'")

    # Flood: sempre verso le scale
    if event_type == "Flood":
        safe = [n for n, d in G.nodes(data=True) if d.get("node_type") == "stairs"]
        logger.info(f"(Flood) Safe nodes (stairs): {safe}")
        return safe

    # Outdoor events
    outdoor_events = {"Earthquake", "Hazardous Material", "Severe Weather", "Power Outage"}
    if event_type in outdoor_events:
        safe = [n for n, d in G.nodes(data=True) if d.get("node_type") == "outdoor"]
        logger.info(f"({event_type}) Safe nodes (outdoor): {safe}")
        return safe

    # Fire: zona pericolosa, usa 'x','y'
    if event_type == "Fire":
        cfg = emergency_config["emergencies"]["Fire"]["danger_zone"]
        x1, x2 = cfg["x1"], cfg["x2"]
        y1, y2 = cfg["y1"], cfg["y2"]
        z1, z2 = cfg["z1"], cfg["z2"]
        safe = []
        for n, d in G.nodes(data=True):
            xc = d.get("x")
            yc = d.get("y")
            floor = d.get("floor_level")
            if xc is None or yc is None or floor is None:
                continue
            # includi solo se FUORI dalla zona di Fire
            if not (x1 <= xc <= x2 and y1 <= yc <= y2 and z1 <= floor <= z2):
                safe.append(n)
        logger.info(f"(Fire) Safe nodes outside danger zone: {safe}")
        return safe

    # Fallback generico
    types = PATHFINDING_CONFIG["default_exit_node_types"]
    safe = [n for n, d in G.nodes(data=True) if d.get("node_type") in types]
    logger.warning(f"(Fallback) Event '{event_type}' non gestito, usare default_exit_node_types={types}: {safe}")
    return safe

def handle_evacuations(floor_level: int, alert_nodes: List[int], event_type: Optional[str] = None):
    try:
        logger.info(f"Handling evacuation for floor {floor_level}, nodes {alert_nodes}, event: {event_type}")
        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"No graph loaded for floor {floor_level}")
            return

        safe_nodes = get_safe_nodes_for_event(G, event_type)
        if not safe_nodes:
            logger.warning(f"No safe nodes for floor {floor_level}, event {event_type}")
            return

        logger.debug(f"Computed safe_nodes={safe_nodes}")
        for source in alert_nodes:
            if source not in G:
                logger.warning(f"Alert node {source} not in graph")
                continue
            path = find_shortest_path_to_exit(G, source, safe_nodes)
            if path is None:
                logger.warning(f"No evacuation path found for node {source}; skipping DB update")
            else:
                logger.debug(f"Path for node {source}: {path}")
                update_node_evacuation_path(source, path)
                logger.info(f"Saved evacuation path for node {source}: {path}")
                        
    except Exception as e:
        logger.error(f"Error in handle_evacuations: {e}")
        raise
