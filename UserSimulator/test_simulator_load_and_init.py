import logging
import random
from simulation.simulator import Simulator
from config.config_loader import Config
from db.db import DB
from utils.logger import logger

def test_simulator_load_and_init():
    logger.info("Starting test_simulator_load_and_init")

    config = Config()
    db = DB(dsn="dbname=map_position_db user=postgres password=postgres host=localhost port=5432")
    try:
        db.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return

    simulator = Simulator(db, config, None)

    simulator.load_map()
    logger.info(f"Loaded {len(simulator.nodes)} nodes and {len(simulator.arcs)} arcs")

    simulator.initialize_users()
    logger.info(f"Initialized {len(simulator.users)} users")

    # Print a sample user position
    if simulator.users:
        for uid, user in list(simulator.users.items())[:3]:
            logger.info(f"User {uid} position: ({user.x}, {user.y}, {user.z}), node {user.node['node_id']}")

if __name__ == "__main__":
    test_simulator_load_and_init()
