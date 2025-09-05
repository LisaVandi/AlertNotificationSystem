from typing import List, Optional, Iterable, Tuple
from datetime import timedelta
import math
import networkx as nx

from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import PATHFINDING_CONFIG
from MapManager.app.services.db_reader import (
    get_interfloor_stair_arcs, get_node_attributes
)
from MapViewer.app.services.graph_manager import graph_manager

from MapManager.app.core.event_state import get_current_event

logger = setup_logging("path_calculator", "MapManager/logs/pathCalculator.log")

# ---- utility ----

def _to_seconds(x) -> float:
    if isinstance(x, timedelta):
        return x.total_seconds()
    try:
        if isinstance(x, str) and ":" in x:
            h, m, s = x.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
        return float(x)
    except Exception:
        return 1.0

def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])

def _edge_weight(_u, _v, data) -> float:
    return _to_seconds(data.get("traversal_time", 1.0))

def _select_exit_nodes(G: nx.DiGraph) -> list[int]:
    ev = (get_current_event() or "").lower()
    # Per Flood: target = scale al piano 0
    if ev == "flood":
        exits = []
        for n, d in G.nodes(data=True):
            if d.get("node_type") != "stairs":
                continue
            fl = d.get("floor_level")
            floors = set(fl if isinstance(fl, list) else [fl]) if fl is not None else set()
            if 0 in floors:
                exits.append(n)
        logger.info(f"[pf] exits(FLOOD) -> stairs@0: {exits}")
        return exits

    # Default: come da config (di solito outdoor)
    exit_types = set(PATHFINDING_CONFIG.get("default_exit_node_types", ["outdoor"]))
    exits = [n for n, d in G.nodes(data=True) if d.get("node_type") in exit_types]
    logger.info(f"[pf] exits(default={sorted(exit_types)}) -> {exits}")
    return exits

STAIR_XY_TOLERANCE = float(PATHFINDING_CONFIG.get("stair_xy_tolerance", 80.0))
MAX_NODE_CAPACITY = int(PATHFINDING_CONFIG.get("max_node_capacity", 10**9))

# ---- floors discovery via inter-floor arcs ----

def _reachable_floors_from(start_floors: Iterable[int]) -> List[int]:
    """
    Scopre tutti i piani raggiungibili **usando gli archi scale inter-piano dal DB**.
    """
    start = {int(f) for f in (start_floors or [])}
    if not start:
        return []

    inter = get_interfloor_stair_arcs()
    if not inter:
        return sorted(start)

    node_ids = {e["initial_node_id"] for e in inter} | {e["final_node_id"] for e in inter}
    attrs = get_node_attributes(list(node_ids))

    # calcola le adiacenze tra piani a partire dagli archi scale
    edges_floor: List[Tuple[int, int]] = []
    for e in inter:
        n1 = attrs.get(e["initial_node_id"]); n2 = attrs.get(e["final_node_id"])
        if not n1 or not n2:
            continue
        f1s = n1["floor_level"]; f2s = n2["floor_level"]
        for f1 in f1s:
            for f2 in f2s:
                if f1 != f2:
                    edges_floor.append((int(f1), int(f2)))

    # BFS sui piani
    visited = set()
    stack = list(start)
    while stack:
        fl = stack.pop()
        if fl in visited:
            continue
        visited.add(fl)
        for a, b in edges_floor:
            if a == fl and b not in visited:
                stack.append(b)
            elif b == fl and a not in visited:
                stack.append(a)

    return sorted(visited)

# ---- build combined graph (multi-piano) ----

def _build_combined_graph(start_floors: Iterable[int]) -> nx.DiGraph:
    floors = _reachable_floors_from(start_floors) or list(start_floors or [])
    floors = list(sorted(set(int(f) for f in floors)))
    logger.info(f"Piani combinati: {floors}")

    # unisci i grafi intra-piano
    G = nx.DiGraph()
    for fl in floors:
        Gfl = graph_manager.get_graph(fl)
        if Gfl is not None:
            G.update(Gfl)

    # aggiungi archi inter-piano (solo scale)
    inter = get_interfloor_stair_arcs()
    if inter:
        node_ids = {e["initial_node_id"] for e in inter} | {e["final_node_id"] for e in inter}
        attrs = get_node_attributes(list(node_ids))
        floors_set = set(floors)

        for e in inter:
            i = e["initial_node_id"]; f = e["final_node_id"]
            if i not in G or f not in G:
                continue
            n1 = attrs.get(i); n2 = attrs.get(f)
            if not n1 or not n2:
                continue

            # almeno uno degli endpoint deve stare su uno dei piani combinati
            f1 = set(n1["floor_level"]); f2 = set(n2["floor_level"])
            if f1.isdisjoint(floors_set) and f2.isdisjoint(floors_set):
                continue

            # tolleranza spaziale (per sicurezza; gli archi nel DB dovrebbero già essere corretti)
            if _dist((n1["x"], n1["y"]), (n2["x"], n2["y"])) > STAIR_XY_TOLERANCE:
                continue

            if not e["active"]:
                continue

            G.add_edge(
                i, f,
                arc_id=int(e["arc_id"]),
                traversal_time=_to_seconds(e["traversal_time"]),
                active=True
            )

    logger.info(f"Grafo multi-piano: {G.number_of_nodes()} nodi, {G.number_of_edges()} archi")    
    return G

# ---- pathfinding ----

def find_shortest_path_to_exit(
    G_floor: nx.DiGraph, start_node: int, exit_nodes: List[int]
) -> Optional[List[int]]:
    """
    Ritorna gli arc_id del percorso più veloce dal nodo di partenza
    a QUALSIASI nodo in exit_nodes, attraversando scale e piani diversi.
    """
    if start_node not in G_floor:
        logger.warning(f"Start node {start_node} non nel grafo del piano")
        return None

    # piani di partenza del nodo
    start_floors = G_floor.nodes[start_node].get("floor_level")
    start_floors = start_floors if isinstance(start_floors, list) else [start_floors]
    start_floors = [int(f) for f in start_floors if f is not None]

    G = _build_combined_graph(start_floors)
    if start_node not in G:
        logger.error(f"Start node {start_node} non nel grafo combinato")
        return None

    # filtra archi inattivi
    for u, v, data in list(G.edges(data=True)):
        if data.get("active") is False:
            G.remove_edge(u, v)

    # rimuovi nodi sovraffollati (eccetto lo start)
    overcrowded = [
        n for n, d in G.nodes(data=True)
        if d.get("current_occupancy", 0) >= MAX_NODE_CAPACITY and n != start_node
    ]
    if overcrowded:
        G.remove_nodes_from(overcrowded)

    # tieni solo i target presenti
    targets = [t for t in (exit_nodes or []) if t in G]
    if not targets:
        logger.warning("Nessun target presente nel grafo combinato")
        return None

    # super-sink per dijkstra multi-target
    super_sink = object()
    G2 = G.copy()
    for t in targets:
        G2.add_edge(t, super_sink, traversal_time=0.0, arc_id=None, active=True)

    try:
        nodes_path = nx.dijkstra_path(G2, source=start_node, target=super_sink, weight=_edge_weight)
    except nx.NetworkXNoPath:
        logger.warning(f"Nessun path dal nodo {start_node} a target")
        return None

    # estrai arc_id, ignora l'ultimo verso il super_sink
    arc_ids: List[int] = []
    for u, v in zip(nodes_path, nodes_path[1:]):
        data = G2.get_edge_data(u, v) or {}
        if data.get("arc_id") is not None:
            arc_ids.append(int(data["arc_id"]))

    if not arc_ids:
        return None

    try:
        total = nx.dijkstra_path_length(G2, start_node, super_sink, weight=_edge_weight)
        logger.info(f"Path migliore da {start_node}: {len(arc_ids)} archi, {total:.1f}s")
    except Exception:
        pass

    return arc_ids
