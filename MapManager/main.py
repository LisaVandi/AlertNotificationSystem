import os
import logging
import psycopg2

from MapManager.app.consumer.rabbitmq_consumer import EvacuationConsumer
from MapViewer.app.services.graph_manager import graph_manager
from MapManager.app.core.manager import initialize_evacuation_paths
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import RABBITMQ_CONFIG
from MapViewer.app.config.settings import DATABASE_CONFIG   
from NotificationCenter.app.handlers.alerted_users_consumer import AlertedUsersConsumer
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler

logger = setup_logging("map_manager_main", "MapManager/logs/mapManager.log")

def preload_graphs():
    """
    Load all floor graphs from database into memory.
    """
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    try:
        with graph_manager.lock:
            graph_manager.graphs.clear()
            logger.info("Cleared graphs in memory.")

        cur.execute("SELECT DISTINCT floor_level FROM nodes")
        floors = [row[0] for row in cur.fetchall()]

        for floor in floors:
            cur.execute("""
                SELECT node_id, x1, x2, y1, y2, node_type, current_occupancy, capacity, floor_level
                FROM nodes WHERE floor_level = %s
            """, (floor,))
            nodes_db = cur.fetchall()
            
            nodes = []
            for r in nodes_db:
                node_id, x1, x2, y1, y2, node_type, occ, cap, floor_level = r
                x_center = (x1 + x2) / 2
                y_center = (y1 + y2) / 2
                nodes.append({
                    "id": node_id,
                    "x": x_center,
                    "y": y_center,
                    "node_type": node_type,
                    "current_occupancy": occ,
                    "capacity": cap,
                    "floor_level": floor_level
                })

            cur.execute("""
                SELECT arc_id, initial_node, final_node, x1, y1, x2, y2, active
                FROM arcs
                WHERE initial_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
                AND final_node IN (SELECT node_id FROM nodes WHERE floor_level = %s)
            """, (floor, floor))
            arc_rows = cur.fetchall()

            arcs = []
            for r in arc_rows:
                arc_id, initial_node, final_node, x1, y1, x2, y2, active = r
                arcs.append({
                    "arc_id": arc_id,
                    "initial_node": initial_node,
                    "final_node": final_node,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "active": active
                })

            graph_manager.load_graph(floor, nodes, arcs)
            logger.info(f"Loaded floor {floor} with {len(nodes)} nodes and {len(arcs)} arcs")

    finally:
        cur.close()
        conn.close()

def main():
    logger.info("Starting MapManager service")
    preload_graphs()

    # Initialize default evacuation paths for each floor graph
    for floor in graph_manager.graphs.keys():
        initialize_evacuation_paths(floor)

    logger.info("Initialization completed. MapManager ready and listening.")

    
    try:
        rabbitmq_handler = RabbitMQHandler(
            host=RABBITMQ_CONFIG["host"],
            port=RABBITMQ_CONFIG["port"],
            username=RABBITMQ_CONFIG["username"],
            password=RABBITMQ_CONFIG["password"])
        logger.info("RabbitMQ consumer initialization for evacuations")
        
        # Consumer for ALERT_QUEUE
        alert_consumer = EvacuationConsumer(rabbitmq_handler)
        alert_consumer.start_consuming()
            
        # Consumer for ALERTED_USERS_QUEUE 
        alerted_users_consumer = AlertedUsersConsumer(rabbitmq_handler)
        alerted_users_consumer.start_consuming()
    
    except Exception as e:
        logger.error(f"Error during consumer initialization: {str(e)}")
        raise

if __name__ == "__main__":
    main()
