import logging
import networkx as nx
from typing import List

from MapManager.app.config.settings import PATHFINDING_CONFIG
from MapManager.app.services.path_calculator import find_shortest_path_to_exit
from MapViewer.app.services.graph_manager import graph_manager
from MapManager.app.services.db_writer import update_node_evacuation_path

logger = logging.getLogger(__name__)

def handle_evacuations(floor_level: int, nodes_in_alert: List[int]):
    try:
        logger.info(f"Inizio calcolo evacuazioni per floor {floor_level}, nodi coinvolti: {nodes_in_alert}")
        
        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"Nessun grafo in memoria per il piano {floor_level}")
            return

        exit_nodes = [n for n, data in G.nodes(data=True)
                      if data.get("node_type") in PATHFINDING_CONFIG["default_exit_node_types"]]

        if not exit_nodes:
            logger.warning(f"Nessun nodo di uscita trovato per piano {floor_level}")
            return

        for source_node in nodes_in_alert:
            if source_node not in G:
                logger.warning(f"Il nodo {source_node} non esiste nel grafo")
                continue

            path = find_shortest_path_to_exit(G, source_node, exit_nodes)
            if path:
                update_node_evacuation_path(source_node, path)
                logger.info(f"Evacuation path per nodo {source_node}: {path}")
            else:
                logger.warning(f"Nessun percorso trovato per nodo {source_node}")

    except Exception as e:
        logger.error(f"Errore durante handle_evacuations: {str(e)}")
        raise
