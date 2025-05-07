import cv2
import numpy as np
import psycopg2
import math
import json
import os

from MapViewer.app.config.logging import setup_logging
from MapViewer.app.config.settings import DATABASE_CONFIG

# Logging setup
logger = setup_logging("graph_extractor", "MapViewer/logs/graph_extractor.log")

# Load Z ranges config
Z_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "z_ranges_config.json")
with open(Z_CONFIG_PATH) as f:
    Z_RANGES = json.load(f)

# Load Room Types config
ROOM_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "node_types_config.json")
with open(ROOM_CONFIG_PATH) as f:
    ROOM_TYPES = json.load(f)["node_types"]

def extract_nodes_and_edges_from_map(image_path, floor_level):
    """
    Extracts nodes (rooms) and edges (connections) from a map image.

    Args:
        image_path (str): The file path to the map image.
        floor_level (int): The floor level associated with the map.

    Returns:
        tuple: A tuple containing:
            - nodes (list of dict): Rooms with coordinates and metadata.
            - arcs (list of dict): Connections between rooms.
    """
    logger.info(f"Processing image: {image_path} | floor_level: {floor_level}")

    # Read image and convert to grayscale
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Could not load image: {image_path}")
        return [], []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    # Find contours in the image
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
            logger.warning(f"No contours found in image: {image_path}")
            return [], []

    # Calculate Z-range dynamically
    base_z = Z_RANGES.get("base_z", 0)
    height_per_floor = Z_RANGES.get("height_per_floor", 3)
    start_from_zero = Z_RANGES.get("z_start_at_floor_zero", False)
    if start_from_zero:
        z1 = base_z + floor_level * height_per_floor
    else:
        z1 = base_z + (floor_level - 1) * height_per_floor
    z2 = z1 + height_per_floor

    nodes = []
    centroids = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < 500:
            continue

        area = w * h
        default_type = "classroom"

        # Regola semplice: 1 persona ogni 2.5 m², assumendo 1 px ≈ 10 cm
        # Calcolo esemplificativo (aggiustabile in base alla scala reale)
        capacity = max(1, area // 250)  # ogni 250 px² corrisponde a ~1 posto

        node = {
            "x1": x,
            "x2": x + w,
            "y1": y,
            "y2": y + h,
            "z1": z1,
            "z2": z2,
            "floor_level": floor_level,
            "capacity": int(capacity),
            "node_type": default_type, 
            "current_occupancy": 0
        }
        nodes.append(node)
        centroids.append(((x + x + w) // 2, (y + y + h) // 2))

    # Generate arcs based on centroid proximity
    arcs = []
    threshold_dist = 200  # max distance for connection

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            c1 = centroids[i]
            c2 = centroids[j]
            dist = math.dist(c1, c2)
            if dist <= threshold_dist:
                arcs.append({
                    "x1": c1[0], "y1": c1[1],
                    "x2": c2[0], "y2": c2[1],
                    "z1": z1, "z2": z2,
                    "capacity": 5,
                    "flow": 0,
                    "traversal_time": f"{int(dist)} seconds",
                    "active": True,
                    "initial_node_index": i,
                    "final_node_index": j
                })

    return nodes, arcs

def insert_graph_into_db(nodes, arcs, floor_level):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()

    node_ids = []

    try:
        for node in nodes:
            cur.execute("""
                INSERT INTO nodes (x1, x2, y1, y2, z1, z2, floor_level, capacity, node_type, current_occupancy)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING node_id
            """, (
                node.get("x1"), node.get("x2"),
                node.get("y1"), node.get("y2"),
                node.get("z1"), node.get("z2"),
                floor_level,
                node.get("capacity", 1),  # default value if missing
                node.get("node_type", "classroom"),  # default value
                node.get("current_occupancy", 0)  # default value
            ))
            node_ids.append(cur.fetchone()[0])

        for arc in arcs:
            cur.execute("""
                INSERT INTO arcs (
                    flow, traversal_time, active, x1, x2, y1, y2,
                    z1, z2, capacity, initial_node, final_node
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING arc_id
            """, (
                arc.get("flow", 0),
                arc.get("traversal_time", "0 seconds"),
                arc.get("active", True),
                arc.get("x1"), arc.get("x2"),
                arc.get("y1"), arc.get("y2"),
                arc.get("z1"), arc.get("z2"),
                arc.get("capacity", 5),
                node_ids[arc["initial_node_index"]],
                node_ids[arc["final_node_index"]]
            ))
            arc_id = cur.fetchone()[0]
            
            cur.execute("""
            INSERT INTO arc_status_log (arc_id, previous_state, new_state, modified_by)
            VALUES (%s, %s, %s, %s)
            """, (
                arc_id,
                None,
                arc.get("active", True),
                "initialization"
            ))

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting graph into DB: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()

    logger.info(f"Inserted {len(nodes)} nodes and {len(arcs)} arcs into the database for floor level {floor_level}.")