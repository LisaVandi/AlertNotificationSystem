import signal
import sys
import threading
import psycopg2

from MapManager.app.consumer.rabbitmq_consumer import EvacuationConsumer
from MapViewer.app.services.graph_manager import graph_manager
from MapManager.app.core.manager import initialize_evacuation_paths
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import RABBITMQ_CONFIG
from MapViewer.app.config.settings import DATABASE_CONFIG   
from NotificationCenter.app.handlers.alerted_users_consumer import AlertedUsersConsumer
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import ACK_EVACUATION_QUEUE
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
        logger.info("RabbitMQHandler (EvacuationConsumer) inizializzato")

        ev_consumer = EvacuationConsumer(rabbit1)
        ev_consumer.start_consuming()

    except Exception as e:
        logger.error(f"Errore in run_evacuation_consumer: {e}")
        rabbit1.close()
        raise

def run_alerted_users_consumer():
    """
    Thread dedicato a AlertedUsersConsumer (consuma da ALERTED_USERS_QUEUE).
    Ogni thread ha la propria connessione/canale RabbitMQ.
    """
    try:
        rabbit2 = RabbitMQHandler(
            host=RABBITMQ_CONFIG["host"],
            port=RABBITMQ_CONFIG["port"],
            username=RABBITMQ_CONFIG["username"],
            password=RABBITMQ_CONFIG["password"]
        )
        logger.info("RabbitMQHandler (AlertedUsersConsumer) inizializzato")
        
        au_consumer = AlertedUsersConsumer(rabbit2)
        au_consumer.start_consuming()

    except Exception as e:
        logger.error(f"Errore in run_alerted_users_consumer: {e}")
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

    # ─── Lancio dei due thread consumer ───
    t1 = threading.Thread(
        target=run_evacuation_consumer,
        name="Thread-EvacuationConsumer",
        daemon=True
    )
    t2 = threading.Thread(
        target=run_alerted_users_consumer,
        name="Thread-AlertedUsersConsumer",
        daemon=True
    )

    t1.start()
    t2.start()

    logger.info("Entrambi i consumer sono stati avviati in thread separati.")
    t1.join()
    t2.join()

if __name__ == "__main__":
    main()

# def main():
#     logger.info("Starting MapManager service")
#     preload_graphs()

#     # Initialize default evacuation paths for each floor graph
#     for floor in graph_manager.graphs.keys():
#         initialize_evacuation_paths(floor, event_type="Earthquake")
#     logger.info("Initialization completed. MapManager ready and listening.")

#     try:
#         rabbitmq_handler = RabbitMQHandler(
#             host=RABBITMQ_CONFIG["host"],
#             port=RABBITMQ_CONFIG["port"],
#             username=RABBITMQ_CONFIG["username"],
#             password=RABBITMQ_CONFIG["password"])
#         logger.info("RabbitMQ consumer initialization for evacuations")
        
#         # Consumer for ALERT_QUEUE
#         alert_consumer = EvacuationConsumer(rabbitmq_handler)
#         alert_consumer.start_consuming()
            
#         # Consumer for ALERTED_USERS_QUEUE 
#         alerted_users_consumer = AlertedUsersConsumer(rabbitmq_handler)
#         alerted_users_consumer.start_consuming()
    
#     except Exception as e:
#         logger.error(f"Error during consumer initialization: {str(e)}")
#         raise

# if __name__ == "__main__":
#     main()
