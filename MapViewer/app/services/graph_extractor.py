import psycopg2
from MapViewer.app.config.logging import setup_logging
from MapViewer.app.config.settings import DATABASE_CONFIG, NODE_TYPES, SCALE_CONFIG, Z_RANGES
from MapViewer.app.services.height_mapper import HeightMapper

logger = setup_logging("graph_extractor", "MapViewer/logs/graph_extractor.log")

def insert_graph_into_db(nodes, arcs, floor_level):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    
    height_mapper = HeightMapper(Z_RANGES, SCALE_CONFIG)
    node_ids = []

    try:
        # Insert nodes into database
        for node in nodes:
            x1_px = node.get("x1")
            x2_px = node.get("x2")
            y1_px = node.get("y1")
            y2_px = node.get("y2")
            
            if node.get("node_type") == "stairs":
                # Calculate the two connected floors (e.g., current and next)
                connected_floors = node.get("connected_floors", [floor_level, floor_level + 1])
                if not isinstance(connected_floors, list):
                    connected_floors = [connected_floors]
                
                # Calculate Z range to cover both floors
                z_min = height_mapper.get_floor_z_range(min(connected_floors))[0]
                z_max = height_mapper.get_floor_z_range(max(connected_floors))[1]
                
                floor_levels = connected_floors
                z1 = int(z_min * 100)
                z2 = int(z_max * 100)
            else:
                floor_levels = [floor_level]
                z_min, z_max = height_mapper.get_floor_z_range(floor_level)
                z1 = int(z_min * 100)
                z2 = int(z_max * 100)
            
            cur.execute("""
                INSERT INTO nodes (x1, x2, y1, y2, z1, z2, floor_level, capacity, node_type, current_occupancy)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING node_id
            """, (
                x1_px, x2_px,
                y1_px, y2_px,
                z1, z2,
                floor_levels,
                node.get("capacity", SCALE_CONFIG["default_node_capacity_per_sqm"]),
                node.get("node_type", "classroom"),
                node.get("current_occupancy", 0)
            ))
            node_ids.append(cur.fetchone()[0])

        # Insert arcs into database
        for arc in arcs:
            initial_index = arc["initial_node_index"]
            final_index = arc["final_node_index"]

            node_start = nodes[initial_index]
            node_end = nodes[final_index]

            # Calcola coordinate centro nodi in px 
            x1 = (node_start["x1"] + node_start["x2"]) // 2
            x2 = (node_end["x1"] + node_end["x2"]) // 2
            y1 = (node_start["y1"] + node_start["y2"]) // 2
            y2 = (node_end["y1"] + node_end["y2"]) // 2

            # Z coordinate da altezza piano
            z1 = int(height_mapper.get_floor_z_range(floor_level)[0] * 100)
            z2 = int(height_mapper.get_floor_z_range(floor_level)[1] * 100)

            # Calcola distanza e capacità in modo coerente
            dx_px = x2 - x1
            dy_px = y2 - y1
            dist_px = (dx_px ** 2 + dy_px ** 2) ** 0.5
            dist_m = height_mapper.pixels_to_model_units(dist_px)  # convert pixels to meters


            passage_width_m = 1.0
            capacity = max(
                1,
                int(dist_m * passage_width_m * SCALE_CONFIG["default_node_capacity_per_sqm"])
            )

            traversal_seconds = max(1, int(dist_m / 1.5))

            cur.execute("""
                INSERT INTO arcs (
                    flow, traversal_time, active,
                    x1, x2, y1, y2, z1, z2,
                    capacity, initial_node, final_node
                ) VALUES (%s, %s, %s,
                          %s, %s, %s, %s, %s, %s,
                          %s, %s, %s)
                RETURNING arc_id
            """, (
                arc.get("flow", 0),
                f"00:00:{traversal_seconds:02d}",
                arc.get("active", True),
                x1, x2, y1, y2,
                z1, z2,
                capacity,
                node_ids[initial_index],
                node_ids[final_index]
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
