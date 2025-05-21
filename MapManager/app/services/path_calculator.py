import networkx as nx
from typing import List, Optional
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import PATHFINDING_CONFIG

def find_shortest_path_to_exit(G: nx.Graph, start_node: int, exit_nodes: List[int]) -> Optional[List[int]]:
    """
    Finds the shortest path from a start node to one of the exit nodes in graph G,
    considering only active edges, node capacity constraints, and returns the ordered list of arc IDs.

    Args:
        G (nx.Graph): NetworkX graph with nodes having 'active' and 'current_occupancy' attributes,
                      and edges having 'active' (bool) and 'arc_id' attributes.
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
        # Copy graph and filter inactive edges
        G_filtered = G.copy()
        for u, v, data in list(G.edges(data=True)):
            if not data.get("active", True):
                G_filtered.remove_edge(u, v)
        
        # Filter out overcrowded nodes
        max_node_capacity = PATHFINDING_CONFIG.get("max_node_capacity", float('inf'))
        overcrowded = [
            n for n, d in G_filtered.nodes(data=True)
            if d.get("current_occupancy", 0) >= max_node_capacity
        ]
        if overcrowded:
            logger.info(f"Removing overcrowded nodes: {overcrowded}")
            G_filtered.remove_nodes_from(overcrowded)

        logger.info(f"Filtered graph has {len(G_filtered.nodes)} nodes and {len(G_filtered.edges)} edges")

        shortest_arc_path = None
        shortest_length = float('inf')

        for target in exit_nodes:
            if target not in G_filtered:
                logger.info(f"Target node {target} not in filtered graph")
                continue
            try:
                # Compute shortest path by traversal_time
                node_path = nx.dijkstra_path(
                    G_filtered, source=start_node, target=target, weight="traversal_time"
                )
                total_len = nx.dijkstra_path_length(
                    G_filtered, source=start_node, target=target, weight="traversal_time"
                )

                # Extract arc IDs
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
