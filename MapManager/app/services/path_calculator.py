import networkx as nx
from collections import deque
from typing import List, Optional, Iterable
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import PATHFINDING_CONFIG
from MapViewer.app.services.graph_manager import graph_manager

logger = setup_logging("path_calculator", "MapManager/logs/pathCalculator.log")


def _as_list(v) -> List[int]:
    """Normalizza floor_level a lista di int."""
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _reachable_floors_from(start_floors: Iterable[int]) -> List[int]:
    """
    Scopre tutti i piani raggiungibili seguendo i nodi 'stairs' come connettori multi-piano.
    Usiamo una BFS sui piani, interrogando graph_manager per ciascun piano scoperto.
    """
    visited = set()
    q = deque(int(fl) for fl in start_floors)
    while q:
        fl = q.popleft()
        if fl in visited:
            continue
        visited.add(fl)

        Gfl = graph_manager.get_graph(fl)
        if Gfl is None:
            continue

        for _, d in Gfl.nodes(data=True):
            if d.get("node_type") == "stairs":
                for nf in _as_list(d.get("floor_level")):
                    if nf not in visited:
                        q.append(int(nf))

    return sorted(visited)


def _build_combined_graph(start_floors: Iterable[int]) -> nx.Graph:
    """
    Crea un grafo combinato unendo i grafi di tutti i piani raggiungibili via scale,
    preservando attributi di nodi e archi.
    """
    floors = _reachable_floors_from(start_floors)
    logger.debug(f"Piani raggiungibili: {floors}")

    combined_G = nx.Graph()
    for fl in floors:
        Gfl = graph_manager.get_graph(fl)
        if not Gfl:
            continue
        combined_G.add_nodes_from(Gfl.nodes(data=True))
        combined_G.add_edges_from(Gfl.edges(data=True))

    logger.info(f"Grafo combinato: {combined_G.number_of_nodes()} nodi, "
                f"{combined_G.number_of_edges()} archi su piani {floors}")
    return combined_G


def find_shortest_path_to_exit(G: nx.Graph, start_node: int, exit_nodes: List[int]) -> Optional[List[int]]:
    """
    Calcola il path più breve (peso: 'traversal_time') da start_node a uno qualunque
    degli exit_nodes, su un grafo multi-piano costruito a partire dal/i piano/i
    del nodo di partenza e da tutti i piani raggiungibili tramite scale.
    Ritorna la lista di arc_id, oppure None se nessun path è disponibile.
    """
    if start_node not in G:
        logger.info(f"Start node {start_node} not in graph")
        return None

    try:
        # Ricava i piani di partenza (int o lista) dal nodo
        start_floors = _as_list(G.nodes[start_node].get("floor_level"))
        if not start_floors:
            all_floors = []
            for _, nfl in G.nodes(data="floor_level"):
                all_floors.extend(_as_list(nfl))
            start_floors = [all_floors[0]] if all_floors else [-1]
            # logger.warning(f"Nodo {start_node} senza 'floor_level': uso solo il grafo corrente")
            # start_floors = [next(iter(_as_list(nfl)) or -1 for _, nfl in G.nodes(data="floor_level"))]

        # Costruisci grafo combinato ricorsivo (tutti i piani raggiungibili via scale)
        combined_G = _build_combined_graph(start_floors)

        # Filtra archi inattivi
        G_filtered = combined_G.copy()
        for u, v, data in list(combined_G.edges(data=True)):
            if not data.get("active", True) and G_filtered.has_edge(u, v):
                G_filtered.remove_edge(u, v)

        # Rimuovi nodi sovraffollati
        max_node_capacity = PATHFINDING_CONFIG.get("max_node_capacity", float("inf"))
        overcrowded = [n for n, d in G_filtered.nodes(data=True)
                       if d.get("current_occupancy", 0) >= max_node_capacity]
        if overcrowded:
            if start_node in overcrowded:
                overcrowded.remove(start_node)
            if overcrowded:
                logger.info(f"Removing overcrowded nodes (except start): {overcrowded}")
                G_filtered.remove_nodes_from(overcrowded)
            
        logger.info(f"Filtered graph has {len(G_filtered.nodes)} nodes and {len(G_filtered.edges)} edges")

        shortest_arc_path = None
        shortest_length = float("inf")

        for target in exit_nodes:
            if target not in G_filtered:
                logger.debug(f"Target node {target} not in filtered graph")
                continue

            try:
                node_path = nx.dijkstra_path(
                    G_filtered, source=start_node, target=target, weight="traversal_time"
                )
                total_len = nx.dijkstra_path_length(
                    G_filtered, source=start_node, target=target, weight="traversal_time"
                )

                # Estrai gli arc_id lungo il path
                arc_path: List[int] = []
                for i in range(len(node_path) - 1):
                    u, v = node_path[i], node_path[i + 1]
                    edge_data = G_filtered.get_edge_data(u, v) or G_filtered.get_edge_data(v, u)
                    if not edge_data:
                        continue
                    # edge_data expected: dict con 'arc_id', 'active', 'traversal_time', ...
                    arc_id = edge_data.get("arc_id")
                    if arc_id is not None:
                        arc_path.append(int(arc_id))

                logger.info(f"Found path {start_node} -> {target} (len={total_len}): {node_path}")

                if total_len < shortest_length and arc_path:
                    shortest_arc_path = arc_path
                    shortest_length = total_len

            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        return shortest_arc_path

    except Exception as e:
        logger.error(f"Error during calculation path from {start_node}: {str(e)}")
        return None
