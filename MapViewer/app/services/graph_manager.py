import networkx as nx
import psycopg2

from threading import Lock
from datetime import timedelta

from MapViewer.app.config.settings import SCALE_CONFIG, Z_RANGES, NODE_TYPES, DATABASE_CONFIG
from MapViewer.app.services.height_mapper import HeightMapper

def time_str_to_seconds(time_val):
    if isinstance(time_val, (int, float)):
        return int(time_val)
    if isinstance(time_val, timedelta):
        return int(time_val.total_seconds())

    s = str(time_val).strip()
    if s.isdigit():
        return int(s)

    parts = s.split(":")
    if len(parts) == 3:
        h, m, sec = parts
        return int(h) * 3600 + int(m) * 60 + int(float(sec))
    return 1

class GraphManager:
    def __init__(self):
        self.graphs = {}
        self.lock = Lock()
        self.height_mapper = HeightMapper(Z_RANGES, SCALE_CONFIG)

    def get_graph(self, floor_level):
        with self.lock:
            if floor_level not in self.graphs:
                self._load_floor_graph(floor_level)
                
            return self.graphs.get(floor_level)

    def add_node(self, x_px: int, y_px: int, floor: int, node_type: str, image_height_px: int) -> dict:
        with self.lock:
            G = self.graphs.setdefault(floor, nx.Graph())

            tolerance_px = 5
            for node_id, data in G.nodes(data=True):
                if abs(data.get('x') - x_px) <= tolerance_px and abs(data.get('y') - y_px) <= tolerance_px:
                    return {
                        "node_id": node_id,
                        "x": data.get('x'),
                        "y": data.get('y'),
                        "floor_level": floor,
                        "node_type": data.get("node_type", node_type),
                        "current_occupancy": data.get("current_occupancy", 0),
                        "capacity": data.get("capacity", 0)
                    }

        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        try:
            delta_px = 10
            x1_px = x_px - delta_px
            x2_px = x_px + delta_px
            y1_px = y_px - delta_px
            y2_px = y_px + delta_px

            z_min, z_max = self.height_mapper.get_floor_z_range(floor)
            z1 = int(z_min * 100)
            z2 = int(z_max * 100)

            cap = NODE_TYPES[node_type].get("capacity", SCALE_CONFIG["default_node_capacity_per_sqm"])

            print(f"Received: x_px={x_px}, y_px={y_px}, image_height_px={image_height_px}")

            cur.execute("""
                INSERT INTO nodes (x1, x2, y1, y2, z1, z2, floor_level, capacity, node_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING node_id
            """, (x1_px, x2_px, y1_px, y2_px, z1, z2, floor, cap, node_type))
            node_id = cur.fetchone()[0]
            conn.commit()

            with self.lock:
                G.add_node(node_id, x=x_px, y=y_px, floor_level=floor, node_type=node_type,
                           current_occupancy=0, capacity=cap)

            return {
                "node_id": node_id,
                "x": x_px,
                "y": y_px,
                "floor_level": floor,
                "node_type": node_type,
                "current_occupancy": 0,
                "capacity": cap
            }
        finally:
            cur.close()
            conn.close()

    def add_edge(self, node1: int, node2: int, floor: int):
        with self.lock:
            G = self.graphs.get(floor)
            if G is None:
                raise ValueError(f"Graph for floor {floor} not found")

            if node1 not in G.nodes or node2 not in G.nodes:
                raise ValueError(f"Nodes {node1} or {node2} not found in the graph")

            if G.has_edge(node1, node2):
                return 

            G.add_edge(node1, node2, active=True)
            self._persist_edge(node1, node2, floor)

    def _persist_edge(self, node1: int, node2: int, floor: int):
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        try:
            G = self.graphs.get(floor)
            if not G:
                raise ValueError("Graph not found.")

            x1_px = G.nodes[node1]['x']
            y1_px = G.nodes[node1]['y']
            x2_px = G.nodes[node2]['x']
            y2_px = G.nodes[node2]['y']

            dx_px = x2_px - x1_px
            dy_px = y2_px - y1_px
            distance_px = (dx_px ** 2 + dy_px ** 2) ** 0.5
            distance_m = self.height_mapper.pixels_to_model_units(distance_px)

            z_min, z_max = self.height_mapper.get_floor_z_range(floor)
            z1 = int(z_min * 100)
            z2 = int(z_max * 100)

            passage_width_m = 1.0

            capacity = max(
                1,
                int(distance_m * passage_width_m * SCALE_CONFIG["default_node_capacity_per_sqm"])
            )

            traversal_seconds = max(1, int(distance_m / 1.5))

            cur.execute("""
                INSERT INTO arcs (
                    flow, traversal_time, active,
                    x1, x2, y1, y2, z1, z2,
                    capacity, initial_node, final_node
                )
                VALUES (%s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s)
                RETURNING arc_id
            """, (
                0, f"00:00:{traversal_seconds:02d}", True,
                x1_px, x2_px, y1_px, y2_px, z1, z2,
                capacity, node1, node2
            ))

            arc_id = cur.fetchone()[0]
            conn.commit()
            print(f"Arco {arc_id} inserito tra nodi {node1} e {node2}")
        finally:
            cur.close()
            conn.close()

    def load_graph(self, floor_level, nodes, arcs):
        with self.lock:
            G = nx.Graph()
            for node in nodes:
                node_id = node.get("id") or node.get("node_id")
                if node_id is None:
                    continue

                px_x = int(node["x"])  
                px_y = int(node["y"])
                
                floors = node.get("floor_level", [floor_level])
                if not isinstance(floors, list):
                    floors = [floors]

                G.add_node(
                    node_id,
                    x=px_x,
                    y=px_y,
                    floor_level=floors,   # <-- lista, non int
                    node_type=node.get("node_type"),
                    current_occupancy=node.get("current_occupancy", 0),
                    capacity=node.get("capacity", 0),
                    safe=node.get("safe", True)
                )
                
            for arc in arcs:
                from_node = arc.get("initial_node")
                to_node = arc.get("final_node")
                if from_node is None or to_node is None:
                    continue
                
                traversal_time_str = arc.get("traversal_time", "00:00:01")
                traversal_time_sec = time_str_to_seconds(traversal_time_str)
                
                G.add_edge(from_node, to_node, active=arc.get("active", True), arc_id=arc.get("arc_id"), traversal_time=traversal_time_sec)
            self.graphs[floor_level] = G
            print(f"Graph for floor {floor_level} loaded with {len(nodes)} nodes and {len(arcs)} arcs")

    def _load_floor_graph(self, floor_level):
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT node_id, x1, x2, y1, y2, node_type, 
                    current_occupancy, capacity, floor_level, safe 
                FROM nodes 
                WHERE %s = ANY(floor_level)
            """, (floor_level,))
            
            nodes = []
            for row in cur.fetchall():
                node_id, x1, x2, y1, y2, node_type, occ, cap, floors, safe = row
                nodes.append({
                    "id": node_id,
                    "x": (x1 + x2) // 2,
                    "y": (y1 + y2) // 2,
                    "node_type": node_type,
                    "current_occupancy": occ,
                    "capacity": cap,
                    "floor_level": floors,
                    "safe": safe
                })
            
            # Carica archi correlati
            cur.execute("""
                SELECT arc_id, initial_node, final_node, active 
                FROM arcs 
                WHERE initial_node IN (
                    SELECT node_id FROM nodes WHERE %s = ANY(floor_level)
                )
            """, (floor_level,))
            
            arcs = []
            for row in cur.fetchall():
                arc_id, initial_node, final_node, active = row
                arcs.append({
                    "arc_id": arc_id,
                    "initial_node": initial_node,
                    "final_node": final_node,
                    "active": active
                })
            
            # Costruisci il grafo
            G = nx.Graph()
            for node in nodes:
                G.add_node(node['id'], **node)
            
            for arc in arcs:
                G.add_edge(arc['initial_node'], arc['final_node'], 
                        arc_id=arc['arc_id'], active=arc['active'])
            
            self.graphs[floor_level] = G    
        finally:
            cur.close()
            conn.close()

graph_manager = GraphManager()
