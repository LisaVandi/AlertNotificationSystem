import networkx as nx
from typing import List, Optional
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import PATHFINDING_CONFIG
from MapViewer.app.services.graph_manager import graph_manager

logger = setup_logging("path_calculator", "MapManager/logs/pathCalculator.log")

def find_shortest_path_to_exit(G: nx.Graph, start_node: int, exit_nodes: List[int]) -> Optional[List[int]]:

    if start_node not in G:
        logger.info(f"Start node {start_node} not in graph")
        return None

    try:
        start_floor = G.nodes[start_node].get("floor_level")[0]
        combined_G = G.copy()

        # Unisci i grafi dei piani connessi tramite scale presenti sul piano di partenza
        stair_nodes = [
            n for n, d in G.nodes(data=True)
            if d.get("node_type") == "stairs"
            and isinstance(d.get("floor_level"), list)
            and len(d["floor_level"]) >= 2
            and start_floor in d["floor_level"]
        ]
        for stair_node in stair_nodes:
            connected_floors = G.nodes[stair_node].get("floor_level", [])
            for floor in connected_floors:
                if floor != start_floor:
                    floor_graph = graph_manager.get_graph(floor)
                    if floor_graph:
                        combined_G.add_nodes_from(floor_graph.nodes(data=True))
                        combined_G.add_edges_from(floor_graph.edges(data=True))

        # Filtra gli archi inattivi sul grafo combinato
        G_filtered = combined_G.copy()
        for u, v, data in list(combined_G.edges(data=True)):
            if not data.get("active", True) and G_filtered.has_edge(u, v):
                G_filtered.remove_edge(u, v)

        # Rimuovi nodi sovraffollati
        max_node_capacity = PATHFINDING_CONFIG.get("max_node_capacity", float('inf'))
        overcrowded = [n for n, d in G_filtered.nodes(data=True)
                       if d.get("current_occupancy", 0) >= max_node_capacity]
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
                node_path = nx.dijkstra_path(G_filtered, source=start_node, target=target, weight="traversal_time")
                total_len = nx.dijkstra_path_length(G_filtered, source=start_node, target=target, weight="traversal_time")

                # Estrai gli arc_id dal grafo filtrato (che contiene anche archi di altri piani)
                arc_path: List[int] = []
                for i in range(len(node_path) - 1):
                    u, v = node_path[i], node_path[i+1]
                    # edge_data può essere dict o dict-of-dict se multigraph: gestiamo il caso semplice
                    edge_data = G_filtered.get_edge_data(u, v)
                    if not edge_data:
                        # prova direzione opposta
                        edge_data = G_filtered.get_edge_data(v, u)
                    if not edge_data:
                        continue
                    # edge_data potrebbe essere p.es. {"arc_id": 12, "active": True, ...}
                    arc_id = edge_data.get("arc_id")
                    if arc_id is not None:
                        arc_path.append(int(arc_id))

                logger.info(f"Found path from {start_node} to {target}: {node_path} with length {total_len}")

                if total_len < shortest_length and arc_path:
                    shortest_arc_path = arc_path
                    shortest_length = total_len

            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        return shortest_arc_path

    except Exception as e:
        logger.error(f"Error during calculation path from {start_node}: {str(e)}")
        return None
