import logging
from typing import List

from MapManager.app.config.settings import PATHFINDING_CONFIG
from MapManager.app.services.path_calculator import find_shortest_path_to_exit
from MapViewer.app.services.graph_manager import graph_manager
from MapManager.app.services.db_writer import update_node_evacuation_path

logger = logging.getLogger(__name__)

def handle_evacuations(floor_level: int, alert_nodes: List[int]):
    """
    Handles evacuation calculations for given nodes.
    Calculates evacuation path for each node and updates the database.
    """
    try:
        logger.info(f"Starting evacuation calculations for floor {floor_level} on nodes: {alert_nodes}")
        
        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"No graph loaded for floor {floor_level}")
            return

        exit_nodes = [n for n, data in G.nodes(data=True)
                      if data.get("node_type") in PATHFINDING_CONFIG["default_exit_node_types"]]
        logger.info(f"Exit nodes found: {exit_nodes}")


        if not exit_nodes:
            logger.warning(f"No exit nodes defined for floor {floor_level}")
            return

        for source_node in alert_nodes:
            if source_node not in G:
                logger.warning(f"Node {source_node} does not exist in graph")
                continue

            path = find_shortest_path_to_exit(G, source_node, exit_nodes)
            if path:
                update_node_evacuation_path(source_node, path)
                logger.info(f"Evacuation path saved for node {source_node}: {path}")
            else:
                logger.warning(f"No evacuation path found for node {source_node}")

    except Exception as e:
        logger.error(f"Error in handle_evacuations: {str(e)}")
        raise

def initialize_evacuation_paths(floor_level: int):
    """
    Initialize and save default evacuation paths for all nodes on the specified floor.
    """
    logger.info(f"Initializing evacuation paths for floor {floor_level}")

    G = graph_manager.get_graph(floor_level)
    if G is None:
        logger.warning(f"No graph loaded for floor {floor_level}")
        return

    exit_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in PATHFINDING_CONFIG["default_exit_node_types"]]
    if not exit_nodes:
        logger.warning(f"No exit nodes defined for floor {floor_level}")
        return

    for node_id in G.nodes():
        path = find_shortest_path_to_exit(G, node_id, exit_nodes)
        if path:
            update_node_evacuation_path(node_id, path)
            logger.info(f"Evacuation path saved for node {node_id}: {path}")
        else:
            update_node_evacuation_path(node_id, [])
            logger.warning(f"No evacuation path found for node {node_id}")
