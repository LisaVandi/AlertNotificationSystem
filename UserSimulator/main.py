import threading
from fastapi import FastAPI
from UserSimulator.config.config_loader import Config
from UserSimulator.db.db import DB
from UserSimulator.rabbitmq.rabbitmq_handler import RabbitMQHandler
from UserSimulator.simulation.simulator import Simulator
from UserSimulator.utils.api import app, simulator_instance
from UserSimulator.utils.logger import logger

config = Config("UserSimulator/config/config.yaml")
db = DB(dsn="dbname=map_position_db user=postgres password=postgres host=localhost port=5432")
simulator = None
rabbitmq = None

@app.on_event("startup")
def on_startup():
    global simulator, rabbitmq, simulator_instance

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
    simulator_instance = simulator

    rabbitmq = RabbitMQHandler(config, simulator)
    simulator.publisher = rabbitmq

    try:
        rabbitmq.connect()
        logger.info("RabbitMQ connected.")
    except Exception as e:
        logger.error(f"RabbitMQ connection failed: {e}", exc_info=True)
        return

    # Start RabbitMQ consumer thread
    threading.Thread(target=rabbitmq.start, daemon=True).start()
    logger.info("RabbitMQ consumer thread started.")

    # Start simulator loop thread
    threading.Thread(target=simulator.run, daemon=True).start()
    logger.info("Simulator thread started.")
