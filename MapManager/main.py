import signal
import sys
import threading
import psycopg2
import os

from MapManager.app.consumer.rabbitmq_consumer import EvacuationConsumer
from MapManager.app.consumer.alert_consumer import AlertConsumer

from MapManager.app.core.manager import initialize_evacuation_paths
from MapManager.app.config.logging import setup_logging

from MapManager.app.config.settings import MAP_ALERTS_QUEUE, MAP_MANAGER_QUEUE, RABBITMQ_CONFIG

from MapViewer.app.services.graph_manager import graph_manager
from MapViewer.app.config.settings import DATABASE_CONFIG   

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_PATH = os.path.join(BASE_DIR, "logs", "mapManager.log")
logger = setup_logging("map_manager_main", LOG_PATH)

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

        cur.execute("SELECT DISTINCT unnest(floor_level) AS floor FROM nodes ORDER BY 1")
        floors = [row[0] for row in cur.fetchall()]

        for floor in floors:
            cur.execute("""
                SELECT node_id, x1, x2, y1, y2, node_type, current_occupancy, capacity, floor_level
                FROM nodes WHERE %s = ANY(floor_level)
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
                SELECT arc_id, initial_node, final_node, x1, y1, x2, y2, active, traversal_time::text AS traversal_time
                FROM arcs
                WHERE initial_node IN (SELECT node_id FROM nodes WHERE %s = ANY(floor_level))
                AND final_node IN (SELECT node_id FROM nodes WHERE %s = ANY(floor_level))
            """, (floor, floor))
            arc_rows = cur.fetchall()

            arcs = []
            for r in arc_rows:
                arc_id, initial_node, final_node, x1, y1, x2, y2, active, traversal_time = r
                arcs.append({
                    "arc_id": arc_id,
                    "initial_node": initial_node,
                    "final_node": final_node,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "active": active,
                    "traversal_time": traversal_time
                })

            graph_manager.load_graph(floor, nodes, arcs)
            logger.info(f"Loaded floor {floor} with {len(nodes)} nodes and {len(arcs)} arcs")

    finally:
        cur.close()
        conn.close()
        
def run_evacuation_consumer():
    """
    Thread dedicato a EvacuationConsumer (consuma da MAP_MANAGER_QUEUE).
    Ogni thread ha la propria connessione/canale RabbitMQ.
    """
    try:
        rabbit1 = RabbitMQHandler(
            host=RABBITMQ_CONFIG["host"],
            port=RABBITMQ_CONFIG["port"],
            username=RABBITMQ_CONFIG["username"],
            password=RABBITMQ_CONFIG["password"]
        )
        rabbit1.declare_queue(MAP_MANAGER_QUEUE)         
        logger.info("RabbitMQHandler (EvacuationConsumer) inizializzato")

        ev_consumer = EvacuationConsumer(rabbit1)
        ev_consumer.start_consuming()

    except Exception as e:
        logger.error(f"Errore in run_evacuation_consumer: {e}")
        rabbit1.close()
        raise
    
def run_alert_consumer():
    try:
        rabbit2 = RabbitMQHandler(
            host=RABBITMQ_CONFIG["host"],
            port=RABBITMQ_CONFIG["port"],
            username=RABBITMQ_CONFIG["username"],
            password=RABBITMQ_CONFIG["password"]
        )
        rabbit2.declare_queue(MAP_ALERTS_QUEUE)   
        logger.info("RabbitMQHandler (AlertConsumer) inizializzato")
        alert_consumer = AlertConsumer(rabbit2)
        alert_consumer.start_consuming()
    except Exception as e:
        logger.error(f"Errore in run_alert_consumer: {e}")
        rabbit2.close()
        raise

def graceful_shutdown(signum, frame):
    logger.info("Shutdown initiated, exiting...")
    sys.exit(0)

def main():
    logger.info("Starting MapManager service")
    preload_graphs()

    # Inizializzazione delle evacuation path di default (evento “Earthquake”)
    for floor in graph_manager.graphs.keys():
        initialize_evacuation_paths(floor, event_type="Earthquake")
    logger.info("Initialization completed. MapManager ready and listening.")

    # Installa il signal handler per Ctrl+C / SIGTERM
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    t1 = threading.Thread(
        target=run_evacuation_consumer,
        name="Thread-EvacuationConsumer",
        daemon=True
    )
    
    t2 = threading.Thread(
        target=run_alert_consumer,
        name="Thread-AlertConsumer",
        daemon=True
    )

    t1.start()
    t2.start()
    
    logger.info("Consumers avviati in thread separati.")
    t1.join()
    t2.join()

if __name__ == "__main__":
    main()

