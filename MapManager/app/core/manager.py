from typing import List, Set, Dict, Tuple
from collections import deque
import psycopg2, yaml

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.app.services.graph_manager import graph_manager

from MapManager.app.config.logging import setup_logging
from MapManager.app.services.db_reader import get_arc_final_node
from MapManager.app.services.path_calculator import find_shortest_path_to_exit
from MapManager.app.services.db_writer import update_node_evacuation_path
from MapManager.app.services.publisher import publish_paths_ready
from MapManager.app.config.settings import ACK_EVACUATION_QUEUE, ALERTS_CONFIG_PATH, PATHFINDING_CONFIG

from MapManager.app.services.db_reader import get_interfloor_stair_arcs, get_node_attributes

logger = setup_logging("evacuation_manager", "MapManager/logs/evacuationManager.log")

try:
    with open(ALERTS_CONFIG_PATH, "r", encoding="utf-8") as f:
        emergency_config = yaml.safe_load(f) or {}
    logger.info(f"Loaded emergency types: {list(emergency_config.get('emergencies', {}).keys())}")
except Exception as e:
    logger.error(f"Cannot load emergency config at {ALERTS_CONFIG_PATH}: {e}")
    emergency_config = {"emergencies": {}}

def get_safe_nodes_for_event(G, event_type: str) -> List[int]:
    emergencies = emergency_config.get("emergencies", {})
    rule = (emergencies or {}).get(event_type, {})
    etype = rule.get("type")
    safe_node_type = rule.get("safe_node_type")
    
    if (event_type or "").lower() == "flood":
        def flist(v): return v if isinstance(v, list) else [v]
        safe = [
            n for n, d in G.nodes(data=True)
            if d.get("node_type") == "stairs"
            and any(int(f) == 0 for f in flist(d.get("floor_level")) if f is not None)
        ]
        logger.info(f"(flood) target = stairs @ floor 0 -> {safe}")
        return safe    

    if not rule or not safe_node_type:
        logger.warning(f"Nessuna regola valida per event='{event_type}'")
        return []

    if etype in ("all", "zone"):
        safe = [n for n, d in G.nodes(data=True) if d.get("node_type") == safe_node_type]
        logger.info(f"({event_type}) target nodes ({safe_node_type}): {safe}")
        return safe

    if etype == "floor":
        danger = {int(x) for x in (rule.get("danger_floors") or [])}
        def flist(v): return v if isinstance(v, list) else [v]
        safe: List[int] = []
        for n, d in G.nodes(data=True):
            if d.get("node_type") != safe_node_type:
                continue
            floors = {int(f) for f in flist(d.get("floor_level")) if f is not None}
            if floors & danger:
                safe.append(n)
        logger.info(f"({event_type}) target ({safe_node_type} in {sorted(danger)}): {safe}")
        return safe

    logger.warning(f"Unhandled rule type '{etype}' for event '{event_type}'")
    return []


def collect_reachable_floors(start_floor: int) -> Set[int]:
    """
    Scopre i piani raggiungibili dal piano di partenza **seguendo gli archi scale inter-piano**.
    """
    inter = get_interfloor_stair_arcs()
    if not inter:
        return {int(start_floor)}

    node_ids = {e["initial_node_id"] for e in inter} | {e["final_node_id"] for e in inter}
    attrs = get_node_attributes(list(node_ids))

    # costruisci adiacenze tra piani
    edges_floor: List[Tuple[int, int]] = []
    for e in inter:
        n1 = attrs.get(e["initial_node_id"]); n2 = attrs.get(e["final_node_id"])
        if not n1 or not n2:
            continue
        for f1 in n1["floor_level"]:
            for f2 in n2["floor_level"]:
                if f1 != f2:
                    edges_floor.append((int(f1), int(f2)))

    # BFS sui piani
    visited: Set[int] = set()
    q: deque[int] = deque([int(start_floor)])
    while q:
        fl = q.popleft()
        if fl in visited:
            continue
        visited.add(fl)
        for a, b in edges_floor:
            if a == fl and b not in visited:
                q.append(b)
            elif b == fl and a not in visited:
                q.append(a)

    return visited


def collect_safe_nodes_multi_floor(start_floor: int, event_type: str) -> List[int]:
    floors = collect_reachable_floors(start_floor)
    combined: List[int] = []
    seen: Set[int] = set()
    for fl in floors:
        Gfl = graph_manager.get_graph(fl)
        if not Gfl: continue
        safe_on_fl = get_safe_nodes_for_event(Gfl, event_type)
        for n in safe_on_fl:
            if n not in seen:
                seen.add(n)
                combined.append(n)
    logger.info(f"Target multi-piano per event={event_type} da floor={start_floor}: {combined}")
    return combined

def _collect_default_exits_multi_floor(start_floor: int) -> List[int]:
    """
    Usa PATHFINDING_CONFIG['default_exit_node_types'] (tipicamente 'outdoor')
    e li raccoglie su TUTTI i piani raggiungibili via scale dal piano di partenza.
    """
    exit_types = set(PATHFINDING_CONFIG.get("default_exit_node_types", []) or [])
    if not exit_types:
        return []
    floors = collect_reachable_floors(start_floor)
    seen, out = set(), []
    for fl in floors:
        Gfl = graph_manager.get_graph(fl)
        if not Gfl:
            continue
        for nid, d in Gfl.nodes(data=True):
            if d.get("node_type") in exit_types and nid not in seen:
                seen.add(nid); out.append(nid)
    return out

def initialize_evacuation_paths(floor_level: int):
    try:
        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"Nessun grafo per il piano {floor_level}")
            return

        exit_types = set(PATHFINDING_CONFIG.get("default_exit_node_types", []) or [])
        if not exit_types:
            logger.info("Nessun default_exit_node_types configurato: init saltata.")
            return

        # 1) outdoor stessi = evacuation_path vuoto
        zeroed = 0
        for nid, d in G.nodes(data=True):
            if d.get("node_type") in exit_types:
                update_node_evacuation_path(nid, [])
                zeroed += 1

        # 2) target multi-piano (outdoor raggiungibili via scale)
        default_targets = _collect_default_exits_multi_floor(floor_level)

        # Fallback: se vuoto, prendi almeno outdoor del piano corrente
        if not default_targets:
            default_targets = [nid for nid, d in G.nodes(data=True) if d.get("node_type") in exit_types]
            if default_targets:
                logger.warning(
                    f"Nessun target multi-piano trovato da floor={floor_level}; "
                    f"uso outdoor locali: {default_targets}"
                )
            else:
                logger.warning(f"Nessun target (outdoor) disponibile per floor={floor_level}")
                return

        # 3) calcolo percorsi per tutti i non-outdoor
        computed = 0
        for nid, d in G.nodes(data=True):
            if d.get("node_type") in exit_types:
                continue
            path = find_shortest_path_to_exit(G, nid, default_targets)
            if path is not None:
                update_node_evacuation_path(nid, path)
                computed += 1
            else:
                logger.warning(f"[init] Nessun path di default per nodo {nid} (piano {floor_level})")

        logger.info(
            f"Init su piano {floor_level}: azzerati target={zeroed}, "
            f"percorsi calcolati={computed} verso default_targets={default_targets}"
        )

    except Exception as e:
        logger.error(f"Errore initialize_evacuation_paths: {e}", exc_info=True)

def get_saved_evacuation_path(node_id: int) -> List[int]:
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT evacuation_path FROM nodes WHERE node_id = %s", (node_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        return row[0] if row and row[0] else []
    except Exception as e:
        logger.error(f"Errore leggendo evacuation_path per nodo {node_id}: {e}")
        return []

# def handle_evacuations(floor_level: int, alert_nodes: List[int], event_type: str, rabbitmq_handler=None):
#     try:
#         logger.info(f"handle_evacuations: floor={floor_level}, event={event_type}, nodes={alert_nodes}")
#         if not alert_nodes: return

#         G = graph_manager.get_graph(floor_level)
#         if G is None:
#             logger.warning(f"Nessun grafo per il piano {floor_level}")
#             return

#         safe_nodes = collect_safe_nodes_multi_floor(floor_level, event_type)
#         if not safe_nodes:
#             logger.warning(f"Nessun nodo target raggiungibile per event={event_type} da piano {floor_level}")
#             return

#         paths_by_node: Dict[int, List[int]] = {}
#         safe_nodes_set = set(safe_nodes)
        
#         for sn in safe_nodes_set:
#             update_node_evacuation_path(sn, [])

#         for source in alert_nodes:
#             if source not in G:
#                 logger.warning(f"Nodo di alert {source} non presente nel grafo del piano {floor_level}")
#                 continue

#             if source in safe_nodes_set:
#                 update_node_evacuation_path(source, [])
#                 continue

#             saved = get_saved_evacuation_path(source)
#             if saved:
#                 last_arc = saved[-1]
#                 final_node = get_arc_final_node(last_arc)
#                 if final_node is not None and final_node in safe_nodes_set:
#                     logger.info(f"Nodo {source} ha già un path verso un target. Skip.")
#                     continue

#             path = find_shortest_path_to_exit(G, source, safe_nodes)
#             if path is None:
#                 logger.warning(f"Nessun path di evacuazione per nodo {source}")
#                 continue

#             update_node_evacuation_path(source, path)
#             paths_by_node[source] = path

#         if rabbitmq_handler:
#             try:
#                 publish_paths_ready(rabbitmq_handler)
#                 logger.info(f"Inviato 'paths_ready' su {ACK_EVACUATION_QUEUE}")
#             except Exception as e:
#                 logger.error(f"Errore pubblicando paths_ready: {e}")

#     except Exception as e:
#         logger.error(f"Errore in handle_evacuations: {e}", exc_info=True)
#         raise


def handle_evacuations(floor_level: int, alert_nodes: List[int], event_type: str, rabbitmq_handler=None):
    try:
        logger.info(f"handle_evacuations: floor={floor_level}, event={event_type}, nodes={alert_nodes}")
        if not alert_nodes:
            return

        G = graph_manager.get_graph(floor_level)
        if G is None:
            logger.warning(f"Nessun grafo per il piano {floor_level}")
            return

        # 1) Target dell’evento corrente (in Flood: SOLO stairs @ floor 0)
        safe_nodes = collect_safe_nodes_multi_floor(floor_level, event_type)
        if not safe_nodes:
            logger.warning(f"Nessun nodo target raggiungibile per event={event_type} da piano {floor_level}")
            return
        safe_nodes_set = set(safe_nodes)

        # 2) Azzera SOLO i target correnti (NON gli outdoor in generale)
        for t in safe_nodes:
            update_node_evacuation_path(t, [])

        paths_by_node: Dict[int, List[int]] = {}

        # 3) Sorgenti = nodi in pericolo (alert_nodes) esclusi i target
        #    (NON filtrare per default_exit_node_types: gli OUTDOOR vanno inclusi!)
        sources = [n for n in alert_nodes if n not in safe_nodes_set]

        for source in sources:
            # opzionale: se il path salvato già termina in un target, salta
            saved = get_saved_evacuation_path(source)
            if saved:
                last_arc = saved[-1]
                final_node = get_arc_final_node(last_arc)
                if final_node is not None and final_node in safe_nodes_set:
                    logger.info(f"Nodo {source} ha già un path verso un target. Skip.")
                    continue

            path = find_shortest_path_to_exit(G, source, safe_nodes)
            if path is None:
                logger.warning(f"Nessun path di evacuazione per nodo {source}")
                continue

            update_node_evacuation_path(source, path)
            paths_by_node[source] = path

        # (invio ACK ecc..)
        if rabbitmq_handler:
            try:
                publish_paths_ready(rabbitmq_handler)
                logger.info(f"Inviato 'paths_ready' su {ACK_EVACUATION_QUEUE}")
            except Exception as e:
                logger.error(f"Errore pubblicando paths_ready: {e}")

    except Exception as e:
        logger.error(f"Errore in handle_evacuations: {e}", exc_info=True)
        raise
