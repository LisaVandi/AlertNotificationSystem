import networkx as nx
from typing import List, Optional

def find_shortest_path_to_exit(G: nx.Graph, start_node: int, exit_nodes: List[int]) -> Optional[List[int]]:
    """
    Finds the shortest path from a starting node to one of the exit nodes in a graph, 
    considering only active edges and using Dijkstra's algorithm.
    Args:
        G (nx.Graph): The input graph represented as a NetworkX graph. 
                      Each edge can have the attributes:
                      - "active" (bool): Indicates if the edge is active (default is True).
                      - "traversal_time" (float): The weight of the edge used for path calculation.
                      - "arc_id" (any): A unique identifier for the edge.
        start_node (int): The starting node ID in the graph.
        exit_nodes (List[int]): A list of node IDs representing possible exit points.
    Returns:
        Optional[List[int]]: A list of arc IDs representing the shortest path to an exit node, 
                             or None if no valid path exists.
    Raises:
        Exception: If an unexpected error occurs during path calculation.
    Notes:
        - The function filters out inactive edges before performing the path calculation.
        - If multiple exit nodes are reachable, the function returns the path to the closest one 
          based on the "traversal_time" weight.
        - If an edge in the path does not have an "arc_id" attribute, it is skipped.
    """
    
    if start_node not in G:
        return None

    try:
        G_filtered = G.copy()
        for u, v, data in list(G.edges(data=True)):
            if not data.get("active", True):
                G_filtered.remove_edge(u, v)

        shortest_arc_path = None
        shortest_length = float('inf')

        for target in exit_nodes:
            if target not in G_filtered:
                continue
            try:
                node_path = nx.dijkstra_path(
                    G_filtered, source=start_node, target=target, weight="traversal_time"
                )
                total_len = nx.dijkstra_path_length(
                    G_filtered, source=start_node, target=target, weight="traversal_time"
                )

                arc_path = []
                for i in range(len(node_path) - 1):
                    u = node_path[i]
                    v = node_path[i + 1]
                    arc_data = G.get_edge_data(u, v)
                    if arc_data is None or "arc_id" not in arc_data:
                        continue 
                    arc_path.append(arc_data["arc_id"])

                if total_len < shortest_length:
                    shortest_arc_path = arc_path
                    shortest_length = total_len

            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        return shortest_arc_path

    except Exception as e:
        print(f"Error during calculation path from {start_node}: {str(e)}")
        return None
