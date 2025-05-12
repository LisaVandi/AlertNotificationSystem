# === config/settings.py ===

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USERNAME = "guest"
RABBITMQ_PASSWORD = "guest"

ALERT_QUEUE = "alert_queue"
MAP_MANAGER_QUEUE = "map_manager_queue"
USER_SIMULATOR_QUEUE = "user_simulator_queue"
POSITION_QUEUE = "position_queue"
ALERTED_USERS_QUEUE = "alerted_users_queue"
EVACUATION_PATHS_QUEUE = "evacuation_paths_queue"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "database": "map_position_db"
}