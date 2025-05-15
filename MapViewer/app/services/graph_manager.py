import networkx as nx
from threading import Lock
import psycopg2
from MapViewer.app.config.settings import SCALE_CONFIG, Z_RANGES, NODE_TYPES, DATABASE_CONFIG
from MapViewer.app.services.height_mapper import HeightMapper

class GraphManager:
    def __init__(self):
        self.graphs = {}  # { floor_level: nx.Graph }
        self.lock = Lock()
        self.height_mapper = HeightMapper(Z_RANGES, SCALE_CONFIG)

    def get_graph(self, floor_level):
        with self.lock:
            return self.graphs.get(floor_level)

    def load_graph(self, floor_level, nodes, arcs):
        G = nx.Graph()
        for node in nodes:
            G.add_node(node['id'], **node)
        for arc in arcs:
            G.add_edge(arc['from'], arc['to'], **arc)
        with self.lock:
            self.graphs[floor_level] = G

    def add_node(self, x_px: int, y_px: int, floor: int, node_type: str) -> dict:
        G = self.graphs.setdefault(floor, nx.Graph())
        tolerance_px = 5

        with self.lock:
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
            tolerance_model_units = self.height_mapper.pixels_to_model_units(tolerance_px) * 100
            x_model = int(self.height_mapper.pixels_to_model_units(x_px) * 100)
            y_model = int(self.height_mapper.pixels_to_model_units(y_px) * 100)

            cur.execute("""
                SELECT node_id FROM nodes
                WHERE floor_level = %s
                  AND abs((x1+x2)/2 - %s) <= %s
                  AND abs((y1+y2)/2 - %s) <= %s
            """, (floor, x_model, tolerance_model_units, y_model, tolerance_model_units))
            row = cur.fetchone()
            if row:
                node_id = row[0]
                with self.lock:
                    G.add_node(node_id, x=x_px, y=y_px, floor_level=floor, node_type=node_type,
                               current_occupancy=0, capacity=NODE_TYPES[node_type].get("capacity", SCALE_CONFIG["default_node_capacity_per_sqm"]))
                return {
                    "node_id": node_id,
                    "x": x_px,
                    "y": y_px,
                    "floor_level": floor,
                    "node_type": node_type,
                    "current_occupancy": 0,
                    "capacity": NODE_TYPES[node_type].get("capacity", SCALE_CONFIG["default_node_capacity_per_sqm"])
                }

            delta_px = 10
            x1_px = x_px - delta_px
            x2_px = x_px + delta_px
            y1_px = y_px - delta_px
            y2_px = y_px + delta_px

            x1 = int(self.height_mapper.pixels_to_model_units(x1_px) * 100)
            x2 = int(self.height_mapper.pixels_to_model_units(x2_px) * 100)
            y1 = int(self.height_mapper.pixels_to_model_units(y1_px) * 100)
            y2 = int(self.height_mapper.pixels_to_model_units(y2_px) * 100)

            z_min, z_max = self.height_mapper.get_floor_z_range(floor)
            z1 = int(z_min * 100)
            z2 = int(z_max * 100)
            cap = NODE_TYPES[node_type].get("capacity", SCALE_CONFIG["default_node_capacity_per_sqm"])

            cur.execute("""
                INSERT INTO nodes (x1, x2, y1, y2, z1, z2, floor_level, capacity, node_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING node_id
            """, (x1, x2, y1, y2, z1, z2, floor, cap, node_type))
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
                print(f"[ERROR] Grafo piano {floor} non trovato in memoria")
                return

            def load_node_from_db(node_id):
                conn = psycopg2.connect(**DATABASE_CONFIG)
                cur = conn.cursor()
                try:
                    cur.execute("""
                        SELECT (x1+x2)/2 AS x, (y1+y2)/2 AS y, node_type, current_occupancy, capacity
                        FROM nodes
                        WHERE node_id = %s
                    """, (node_id,))
                    row = cur.fetchone()
                    if row:
                        x, y, node_type, occ, cap = row
                        G.add_node(node_id, x=x, y=y, floor_level=floor, node_type=node_type,
                                   current_occupancy=occ, capacity=cap)
                        print(f"[DEBUG] Nodo {node_id} caricato da DB in grafo piano {floor}")
                        return True
                    else:
                        print(f"[ERROR] Nodo {node_id} non trovato nel DB")
                        return False
                finally:
                    cur.close()
                    conn.close()

            if node1 not in G.nodes:
                loaded = load_node_from_db(node1)
                if not loaded:
                    print(f"[ERROR] Nodo {node1} mancante e non caricato dal DB, aborto add_edge")
                    return
            if node2 not in G.nodes:
                loaded = load_node_from_db(node2)
                if not loaded:
                    print(f"[ERROR] Nodo {node2} mancante e non caricato dal DB, aborto add_edge")
                    return

            if G.has_edge(node1, node2):
                print(f"[INFO] Arco tra {node1} e {node2} già presente")
                return

            G.add_edge(node1, node2)
            print(f"[DEBUG] Arco aggiunto in memoria, ora persisto nel DB")
            self._persist_edge(node1, node2, floor)

    def _persist_edge(self, node1: int, node2: int, floor: int):
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cur = conn.cursor()
        try:
            G = self.graphs.get(floor)
            if not G:
                raise ValueError("Graph not found for the specified floor level.")

            x1_px = G.nodes[node1]['x']
            y1_px = G.nodes[node1]['y']
            x2_px = G.nodes[node2]['x']
            y2_px = G.nodes[node2]['y']

            dx_px = x2_px - x1_px
            dy_px = y2_px - y1_px
            distance_px = (dx_px ** 2 + dy_px ** 2) ** 0.5
            distance_m = self.height_mapper.pixels_to_model_units(distance_px)
            
            x1_cm = int(self.height_mapper.pixels_to_model_units(x1_px) * 100)
            x2_cm = int(self.height_mapper.pixels_to_model_units(x2_px) * 100)
            y1_cm = int(self.height_mapper.pixels_to_model_units(y1_px) * 100)
            y2_cm = int(self.height_mapper.pixels_to_model_units(y2_px) * 100)
            
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
                x1_cm, x2_cm, y1_cm, y2_cm, z1, z2,
                capacity, node1, node2
            ))

            arc_id = cur.fetchone()[0]
            conn.commit()
            print(f"[DEBUG] Arco {arc_id} inserito nel database tra {node1} e {node2}")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Errore inserimento arco: {e}")
        finally:
            cur.close()
            conn.close()

graph_manager = GraphManager()
