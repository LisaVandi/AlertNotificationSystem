from typing import List, Optional
import yaml

from MapManager.app.config.settings import PATHFINDING_CONFIG
from MapManager.app.services.path_calculator import find_shortest_path_to_exit
from MapViewer.app.services.graph_manager import graph_manager
from MapManager.app.services.db_writer import update_node_evacuation_path
from MapManager.app.config.logging import setup_logging

logger = setup_logging("evacuation_manager", "MapManager/logs/evacuationManager.log")

# Load emergency configuration once at module load time
with open("PositionManager/config/config.yaml", "r") as file:
    emergency_config = yaml.safe_load(file)

def get_safe_nodes_for_event(G, event_type: str) -> List[int]:
    config = emergency_config.get("emergencies", {}).get(event_type, None)
    if not config:
        logger.warning(f"No configuration for event type: {event_type}")
        return []

    event_kind = config.get("type")
    
    if event_kind == "floor":
        danger_floors = config.get("danger_floors", [])
        safe_nodes = [n for n, d in G.nodes(data=True) if d.get("floor_level") not in danger_floors]
        logger.info(f"Safe nodes excluding danger floors {danger_floors}: {safe_nodes}")
        return safe_nodes

    if event_kind == "all":
        safe_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "outdoor"]
        logger.info(f"Safe nodes for 'all' danger: {safe_nodes}")
        return safe_nodes

    if event_kind == "zone":
        zone = config.get("danger_zone", {})
        safe_nodes = []
        for n, d in G.nodes(data=True):
            x_center = (d.get("x1", 0) + d.get("x2", 0)) / 2
            y_center = (d.get("y1", 0) + d.get("y2", 0)) / 2
            floor = d.get("floor_level", 0)
            if not (zone["x1"] <= x_center <= zone["x2"] and
                    zone["y1"] <= y_center <= zone["y2"] and
                    zone["z1"] <= floor <= zone["z2"]):
                safe_nodes.append(n)
        logger.info(f"Safe nodes outside danger zone: {safe_nodes}")
        return safe_nodes

    logger.warning(f"Unknown event kind '{event_kind}', returning empty safe nodes list")
    return []

def handle_evacuations(floor_level: int, alert_nodes: List[int], event_type: Optional[str] = None):
    try:
        logger.info(f"Handling evacuation for floor {floor_level}, nodes {alert_nodes}, event: {event_type}")
        
        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"No graph loaded for floor {floor_level}")
            return

        if event_type:
            safe_nodes = get_safe_nodes_for_event(G, event_type)
        else:
            safe_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in PATHFINDING_CONFIG["default_exit_node_types"]]

        if not safe_nodes:
            logger.warning(f"No safe nodes found for evacuation on floor {floor_level} with event {event_type}")
            return

        for source_node in alert_nodes:
            if source_node not in G:
                logger.warning(f"Alert node {source_node} not found in graph")
                continue

            path = find_shortest_path_to_exit(G, source_node, safe_nodes)
            if path:
                update_node_evacuation_path(source_node, path)
                logger.info(f"Saved evacuation path for node {source_node}: {path}")
            else:
                logger.warning(f"No evacuation path found for node {source_node}")

    except Exception as e:
        logger.error(f"Error in handle_evacuations: {str(e)}")
        raise

def initialize_evacuation_paths(floor_level: int, default_event_type: str = "Evacuation"):
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
        if path:
            update_node_evacuation_path(node_id, path)
            logger.info(f"Saved evacuation path for node {node_id}: {path}")
        else:
            logger.warning(f"No evacuation path found for node {node_id}")
