""" 
This module provides a utility function to extract a graph representation (nodes and arcs)
from the database for a specific floor of a building. The result is a structured dictionary
containing all data necessary to render a floor plan graph, including an image reference,
dimensions, and graph elements.

"""
import psycopg2
import json
import os
from MapViewer.app.config.settings import DATABASE_CONFIG

def get_graph_json(floor_level: int, image_filename: str, image_width: int, image_height: int, output_path: str = None):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT node_id, (x1 + x2) / 2 AS x, (y1 + y2) / 2 AS y
        FROM nodes
        WHERE floor_level = %s
    """, (floor_level,))
    nodes = [{"id": row[0], "x": row[1], "y": row[2]} for row in cur.fetchall()]

    cur.execute("""
        SELECT initial_node, final_node
        FROM arcs
        WHERE initial_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
          AND final_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
    """, (floor_level, floor_level))
    arcs = [{"from": row[0], "to": row[1]} for row in cur.fetchall()]

    cur.close()
    conn.close()

    graph_data = {
        "image": f"img/{image_filename}",
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
