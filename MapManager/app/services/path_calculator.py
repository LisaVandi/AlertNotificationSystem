import networkx as nx
from typing import List, Optional
from MapManager.app.config.logging import setup_logging

def find_shortest_path_to_exit(G: nx.Graph, start_node: int, exit_nodes: List[int]) -> Optional[List[int]]:
    """
    Finds the shortest path from a start node to one of the exit nodes in graph G,
    considering only active edges, and returns the ordered list of arc IDs.

    Args:
        G (nx.Graph): NetworkX graph with edges having 'active' (bool) and 'arc_id' attributes.
        start_node (int): The node ID to start from.
        exit_nodes (List[int]): List of exit node IDs.

    Returns:
        Optional[List[int]]: Ordered list of arc IDs forming the shortest path, or None if no path found.
    """
    logger = setup_logging("path_calculator", "MapManager/logs/pathCalculator.log")
    
    if start_node not in G:
        logger.info(f"Start node {start_node} not in graph")
        return None

    try:
        # Create a copy filtering out inactive edges
        G_filtered = G.copy()
        for u, v, data in list(G.edges(data=True)):
            logger.info(f"Edge ({u}, {v}): {data}")
            if not data.get("active", True):
                G_filtered.remove_edge(u, v)
        
        logger.info(f"Filtered graph has {len(G_filtered.nodes)} nodes and {len(G_filtered.edges)} edges")

        shortest_arc_path = None
        shortest_length = float('inf')

        for target in exit_nodes:
            if target not in G_filtered:
                logger.info(f"Target node {target} not in filtered graph")
                continue
            try:
                node_path = nx.dijkstra_path(G_filtered, source=start_node, target=target, weight="traversal_time")
                total_len = nx.dijkstra_path_length(G_filtered, source=start_node, target=target, weight="traversal_time")

                arc_path = []
                for i in range(len(node_path) - 1):
                    u = node_path[i]
                    v = node_path[i+1]
                    arc_data = G.get_edge_data(u, v)
                    if arc_data is None or "arc_id" not in arc_data:
                        continue
                    arc_path.append(arc_data["arc_id"])
                
                logger.info(f"Found path from {start_node} to {target}: {node_path} with length {total_len}")

                if total_len < shortest_length:
                    shortest_arc_path = arc_path
                    shortest_length = total_len

            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        return shortest_arc_path

    except Exception as e:
        logger.error(f"Error during calculation path from {start_node}: {str(e)}")
        return None
