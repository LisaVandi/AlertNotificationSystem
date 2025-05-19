import networkx as nx
from typing import List, Optional

def find_shortest_path_to_exit(G: nx.Graph, start_node: int, exit_nodes: List[int]) -> Optional[List[int]]:
    """
    Trova il percorso più breve da un nodo di partenza a uno dei nodi di uscita
    restituendo una lista di arc_id (id degli archi) anziché nodi.

    Args:
        G (nx.Graph): Il grafo di input.
        start_node (int): Il nodo di partenza.
        exit_nodes (List[int]): I nodi di uscita.

    Returns:
        Optional[List[int]]: Lista degli arc_id del percorso più breve, 
                             o None se nessun percorso esiste.
    """
    if start_node not in G:
        return None

    try:
        # Calcola il percorso più breve usando Dijkstra
        node_path = nx.dijkstra_path(
            G, source=start_node, target=exit_nodes[0], weight="traversal_time"
        )

        # Converte il percorso in arc_id
        arc_path = []
        for i in range(len(node_path) - 1):
            u = node_path[i]
            v = node_path[i + 1]
            arc_data = G.get_edge_data(u, v)
            if arc_data and "arc_id" in arc_data:
                arc_path.append(arc_data["arc_id"])

        return arc_path

    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
