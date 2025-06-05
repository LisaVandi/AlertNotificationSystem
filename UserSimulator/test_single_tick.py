import logging
from simulation.simulator import Simulator
from config.config_loader import Config
from db.db import DB


def test_single_tick():
    # Setup logger base (se non già fatto)
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()

    # Config e DB (usa i tuoi parametri reali)
    config = Config()
    db = DB(dsn="dbname=map_position_db user=postgres password=postgres host=localhost port=5432")
    db.connect()

    # Crea simulatore senza RabbitMQ (passa None o mock)
    simulator = Simulator(db, config, rabbitmq_handler=None)

    # Carica mappa e inizializza utenti
    simulator.load_map()
    simulator.initialize_users()

    logger.info("Running single tick")
    simulator.tick()
    logger.info("Single tick completed")

    # Mostra alcune posizioni utenti dopo tick
    for user_id, pos in list(simulator.users_positions.items())[:5]:
        logger.info(f"User {user_id} position after tick: {pos}")

if __name__ == "__main__":
    test_single_tick()
