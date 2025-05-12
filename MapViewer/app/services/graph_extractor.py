import cv2
import psycopg2
import math

from MapViewer.app.config.logging import setup_logging
from MapViewer.app.config.settings import DATABASE_CONFIG, SCALE_CONFIG, NODE_TYPES, Z_RANGES
from MapViewer.app.services.height_mapper import HeightMapper

logger = setup_logging("graph_extractor", "MapViewer/logs/graph_extractor.log")
height_mapper = HeightMapper(Z_RANGES, SCALE_CONFIG)

PIXELS_PER_CM = SCALE_CONFIG["pixels_per_cm"]
THRESHOLD_DIST_CM = SCALE_CONFIG["edge_threshold_cm"]
MIN_AREA_PX = SCALE_CONFIG["min_area_px"]
DEFAULT_CAP_PER_SQM = SCALE_CONFIG["default_node_capacity_per_sqm"]
SCALE_FACTOR = SCALE_CONFIG["scale_factor"]

def extract_nodes_and_edges_from_map(image_path, floor_level):
    logger.info(f"Processing image: {image_path} | floor_level: {floor_level}")

    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Could not load image: {image_path}")
        return [], []
    
    units_per_pixel = 1 / PIXELS_PER_CM  # cm per pixel 
    cm_to_m = SCALE_FACTOR / 100 # model cm to real m    
    
    origin_x, origin_y = 0, 0  

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    # Find contours in the image
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
            logger.warning(f"No contours found in image: {image_path}")
            return [], []
    
    # Calculate Z-range using HeightMapper
    z_min_m, z_max_m = height_mapper.get_floor_z_range(floor_level)
    z1 = height_mapper.meters_to_model_units(z_min_m) * 100
    z2 = z1 + (height_mapper.meters_to_model_units(z_max_m - z_min_m) * 100)

    nodes = []
    centroids = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area_pixels = w * h
        if area_pixels < MIN_AREA_PX:
            continue

        # Pixel to model units (cm)
        x1_cm = (x - origin_x) * units_per_pixel
        x2_cm = (x + w - origin_x) * units_per_pixel
        y1_cm = (y - origin_y) * units_per_pixel
        y2_cm = (y + h - origin_y) * units_per_pixel

        width_meters = (x2_cm - x1_cm) * cm_to_m
        height_meters = (y2_cm - y1_cm) * cm_to_m
        area_meters = width_meters * height_meters

        node_type = "classroom"
        capacity = NODE_TYPES.get(node_type, {}).get("capacity")
        if capacity is None:
            capacity = int(area_meters * DEFAULT_CAP_PER_SQM)

        node = {
            "x1": x,
            "x2": x + w,
            "y1": y,
            "y2": y + h,
            "z1": z1,
            "z2": z2,
            "floor_level": floor_level,
            "capacity": int(capacity),
            "node_type": node_type, 
            "current_occupancy": 0
        }
        nodes.append(node)
        centroids.append(((x1_cm + x2_cm) / 2, (y1_cm + y2_cm) / 2)) 

    arcs = []
    threshold_dist = 10 # Distanza massima per il collegamento (in cm nel modello)

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
                    "capacity": 30, # attenzione!!
                    "flow": 0,
                    "traversal_time": f"{int(dist * cm_to_m)} seconds",
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
                arc.get("capacity", 5), # attenzione!!
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