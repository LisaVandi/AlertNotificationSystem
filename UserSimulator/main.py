# UserSimulator/main.py

import threading
from fastapi import FastAPI
from UserSimulator.config.config_loader import Config
from UserSimulator.db.db import DB
from UserSimulator.rabbitmq.rabbitmq_handler import RabbitMQHandler
from UserSimulator.simulation.simulator import Simulator
from UserSimulator.utils.api import register_api_routes
from UserSimulator.utils.logger import logger

# Inizializza FastAPI
app = FastAPI()

# Inizializza istanze principali
config = Config("UserSimulator/config/config.yaml")
db = DB(dsn="dbname=map_position_db user=postgres password=postgres host=localhost port=5432")
simulator = None
rabbitmq = None
simulator_instance_ref = [None]  # Lista mutabile per mantenere il riferimento

# Registra le rotte API
register_api_routes(app, simulator_instance_ref)

@app.on_event("startup")
def on_startup():
    global simulator, rabbitmq

    logger.info("Starting UserSimulator service...")

    try:
        db.connect()
        logger.info("Database connected.")
        nodes = db.get_nodes()
        arcs = db.get_arcs()
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        return

    simulator = Simulator(config, nodes, arcs)
    simulator_instance_ref[0] = simulator  # Salva il riferimento accessibile da API

    rabbitmq = RabbitMQHandler(config, simulator)
    simulator.publisher = rabbitmq

    try:
        rabbitmq.connect()
        logger.info("RabbitMQ connected.")
    except Exception as e:
        logger.error(f"RabbitMQ connection failed: {e}", exc_info=True)
        return

    # Avvia i thread in background
    threading.Thread(target=rabbitmq.start, daemon=True).start()
    logger.info("RabbitMQ consumer thread started.")

    threading.Thread(target=simulator.run, daemon=True).start()
    logger.info("Simulator thread started.")

# Avvio diretto con uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("UserSimulator.main:app", host="0.0.0.0", port=8001, reload=False)
