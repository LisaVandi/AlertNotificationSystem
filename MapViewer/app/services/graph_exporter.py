import json
import psycopg2
import os
from MapViewer.app.config.settings import DATABASE_CONFIG

def get_graph_json(floor_level: int, image_filename: str, image_width: int, image_height: int, output_path: str = None):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT node_id, x1, x2, y1, y2, node_type, current_occupancy, capacity
            FROM nodes
            WHERE floor_level = %s
        """, (floor_level,))
        nodes_db = cur.fetchall()
        
        nodes = []
        for row in nodes_db:
            node_id, x1, x2, y1, y2, node_type, occ, cap = row
            x_center = (x1 + x2) / 2
            y_center = (y1 + y2) / 2
            nodes.append({
                "id": node_id,
                "x": x_center,
                "y": y_center,
                "node_type": node_type,
                "current_occupancy": occ,
                "capacity": cap
            })

        cur.execute("""
            SELECT arc_id, initial_node, final_node, x1, y1, x2, y2, active
            FROM arcs
            WHERE initial_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
            AND final_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
        """, (floor_level, floor_level))
        arcs = [{ "arc_id": row[0], "from": row[1], "to": row[2], "x1": row[3], "y1": row[4], "x2": row[5], "y2": row[6], "active": row[7]} for row in cur.fetchall()]
    except Exception as e:
        raise

    graph_data = {
        "image": f"/static/img/{image_filename}",
        "imageWidth": image_width,
        "imageHeight": image_height,
        "nodes": nodes,
        "arcs": arcs
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(graph_data, f, indent=2)

    return graph_data
